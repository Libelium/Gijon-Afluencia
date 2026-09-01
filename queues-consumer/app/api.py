"""
HTTP surface of the queues-consumer.

Access control notes (SEC-016, SEC-017, SEC-018, SEC-043)
---------------------------------------------------------
This service is deployed as a ClusterIP with no Gateway route, so what follows
protects against lateral movement from another pod, not against the Internet.
That degrades the urgency, not the validity: a compromised container reached all
four of the defects below.

* SEC-043  CORS was `allow_origins=["*"]` together with `allow_credentials=True`.
           Now an explicit allow list, and credentials are only enabled when at
           least one origin is configured.
* SEC-017  `/publish` dispatched ANY Celery task by name, unauthenticated. Now
           requires the shared secret and the task must be in an allow list.
* SEC-016  `/test-connection` was an unauthenticated SSRF: it forwarded to any
           URL, method, headers and body supplied by the caller and returned the
           response. It had no caller anywhere in the platform, so it is gone.
* SEC-018  `/stream/{pipeline_id}/{entity_id}/{file}` concatenated `file` into
           `os.path.join` unsanitised. Now the name must match a strict HLS
           pattern and the resolved path is asserted to stay inside the output
           directory, plus the same authentication as /publish.

The shared secret is fail-closed on purpose: an unset `QUEUES_CONSUMER_API_TOKEN`
makes the protected endpoints answer 503, it does not make them public. That is
the same mistake SEC-025 flagged in fiware-manager (`if not expected: return True`),
and it is not repeated here.
"""

import hmac
import os
import re
from inspect import Parameter, signature
from typing import Any

from config.logging import appLogging as logging
from config.celery import app as celery_app
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import Response, FileResponse
from schemas.context_broker_notification_schema import ContextBrokerNotification
from schemas.fiware_subscription_schema import TypeSubscriptionMessage
from schemas.task_request_schema import TaskRequest
from tasks.sync import fiware_orion_subscription_job, fiware_type_subscription_job
from fastapi.middleware.cors import CORSMiddleware
from config.config import settings


application = FastAPI(
    docs_url="/docs" if settings.ENABLE_SWAGGER else None,
    redoc_url="/redoc" if settings.ENABLE_SWAGGER else None,
    openapi_url="/openapi.json" if settings.ENABLE_SWAGGER else None,
)


# --------------------------------------------------------------------------- #
# SEC-043 - CORS
# --------------------------------------------------------------------------- #
# `allow_origins=["*"]` with `allow_credentials=True` is the combination the
# CORS spec forbids: Starlette resolves the wildcard to the caller's own Origin
# and echoes it back with Access-Control-Allow-Credentials, so any site a browser
# visits could issue credentialed cross-origin calls to this API.
origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

if origins:
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Queues-Consumer-Token"],
    )
else:
    logging.info(
        "CORS_ALLOWED_ORIGINS is empty: no cross-origin browser access is granted."
    )


# --------------------------------------------------------------------------- #
# SEC-017 / SEC-018 - shared-secret authentication
# --------------------------------------------------------------------------- #
def require_api_token(
    x_queues_consumer_token: str = Header(default=""),
) -> None:
    """
    Fail-closed shared-secret check for the endpoints that trigger work or read
    files off disk.

    An unconfigured secret is a deployment error, not a licence to serve the
    endpoint openly, so it answers 503.
    """
    expected = settings.QUEUES_CONSUMER_API_TOKEN

    if not expected:
        logging.error(
            "QUEUES_CONSUMER_API_TOKEN is not configured: refusing the request. "
            "Set it on this service and on every caller."
        )
        raise HTTPException(
            status_code=503, detail="Service is not configured for authenticated access"
        )

    # compare_digest keeps the comparison constant-time.
    if not hmac.compare_digest(x_queues_consumer_token, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


# --------------------------------------------------------------------------- #
# SEC-017 - allow list of dispatchable tasks
# --------------------------------------------------------------------------- #
# `celery_app.tasks[task_name]` accepts anything registered in the worker,
# including Celery's own built-ins (celery.backend_cleanup, celery.chord, ...),
# so an attacker who could reach /publish chose the code that ran. Only the
# tasks the platform actually publishes over HTTP belong here.
PUBLISHABLE_TASKS_DEFAULT = frozenset(
    {
        "platform.data.importation_job",
        "platform.sync.fiware_type_subscription_job",
        "platform.entity_groups.update",
        "platform.push-notifications.send",
    }
)


def _publishable_tasks() -> frozenset:
    configured = {t.strip() for t in settings.PUBLISHABLE_TASKS.split(",") if t.strip()}
    return frozenset(configured) if configured else PUBLISHABLE_TASKS_DEFAULT


@application.get("/hchk")
def health_check():
    return "OK"


@application.post("/orion-ld/subscription", status_code=204)
async def subscription(request: Request):
    # Called by Orion-LD itself as a subscription notification target, so it
    # cannot carry our shared secret. Left as-is deliberately.
    try:
        json_body = await request.json()

        notification = ContextBrokerNotification(
            headers=request.headers, body=json_body
        )

        fiware_orion_subscription_job.delay(notification)
    except Exception as e:
        logging.error(e)

    # Always return 204 because the context broker might ban the subscription
    # if it doesn't receive a successful response for a series of attempts
    return Response(status_code=204)


@application.post("/publish", status_code=204, dependencies=[Depends(require_api_token)])
def publish_request(request: TaskRequest, response: Response) -> None:

    def cast_param_to(received_params: dict, expected_param: Parameter) -> Any:
        """
        Cast the received parameters to the expected parameters,
        using the expected parameters' annotations and default values
        """
        param_type = expected_param.annotation
        param_name = expected_param.name
        param_default = expected_param.default

        received_param = received_params.get(param_name, None)

        if received_param is None:
            return param_default

        # Primitive types (int, str, float, bool) can't be unpacked with **
        if param_type in (int, str, float, bool):
            return param_type(received_param)

        return param_type(**received_param)

    # get the task from the celery module
    task_name = request.task

    # SEC-017. Check the allow list before touching the registry, so an
    # unknown name never reaches `celery_app.tasks[...]`.
    if task_name not in _publishable_tasks():
        logging.warning(f"Rejected publish request for non-publishable task {task_name}")
        raise HTTPException(status_code=403, detail="Task is not publishable")

    # get the task parameters
    task_params = request.params

    task = celery_app.tasks.get(task_name)
    if task is None:
        # Allow-listed but not registered in this worker role: a configuration
        # problem, not a client error. Previously this was a bare KeyError -> 500.
        logging.error(f"Task {task_name} is allow-listed but not registered")
        raise HTTPException(status_code=503, detail="Task is not available")

    sig = signature(task)

    true_params = {}
    # if there is only one parameter, we assume that the request.params
    # is the parameter itself
    if len(sig.parameters) == 1:
        param = list(sig.parameters.values())[0]
        param_name = param.name
        task_params = {param_name: request.params}

    for param in sig.parameters.values():
        try:
            true_params[param.name] = cast_param_to(task_params, param)
        except Exception as e:
            logging.error(e)
            return Response(
                status_code=400, content=f"Error in task parameter: {param.name}"
            )

    task.delay(**true_params)

    # return a 204 response
    return Response(status_code=204)


# SEC-016. `/test-connection` used to live here. It read url/method/headers/body
# straight out of the request body and called `requests.request(...)` with them,
# unauthenticated, returning the upstream response to the caller - a textbook
# SSRF that reached the cloud metadata endpoint, every ClusterIP service and
# every internal admin API from inside the cluster.
#
# It is removed rather than gated: a repository-wide search found no caller in
# the backend, the frontend, the charts or the compose files, so it was
# development scaffolding that shipped. If a connectivity probe is ever needed,
# reintroduce it behind `require_api_token` AND an allow list of destination
# hosts resolved to their IPs, rejecting private and link-local ranges.


# --------------------------------------------------------------------------- #
# SEC-018 - HLS playlist and segments
# --------------------------------------------------------------------------- #
# Only the file names an HLS packager actually produces. No path separators, no
# dots beyond the extension, so "../.." and absolute paths cannot be expressed.
_HLS_FILE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}\.(m3u8|ts|m4s|mp4|vtt)$")


@application.get(
    "/stream/{pipeline_id}/{entity_id}/{file}",
    dependencies=[Depends(require_api_token)],
)
async def get_hls_file(pipeline_id: int, entity_id: int, file: str):
    logging.info(
        f"Requesting file for pipeline_id: {pipeline_id}, entity_id: {entity_id}, output_type: {file}"
    )

    if not _HLS_FILE_RE.match(file):
        # Rejected before the name reaches os.path.join. `os.path.join(base,
        # "/etc/passwd")` returns "/etc/passwd" - an absolute component discards
        # everything before it - so the previous code was traversable with a
        # single leading slash, not only with "../".
        logging.warning(f"Rejected stream file name: {file!r}")
        raise HTTPException(status_code=404, detail="File not found")

    base_dir = os.path.realpath(settings.STREAMING_OUTPUT_DIR)
    filename = f"pipeline_{pipeline_id}/entity_{entity_id}/{file}"
    file_path = os.path.realpath(os.path.join(base_dir, filename))

    # Belt and braces: even with the pattern above, confirm the resolved path -
    # symlinks included - is still under the output directory.
    if os.path.commonpath([base_dir, file_path]) != base_dir:
        logging.warning(f"Rejected stream path outside the output dir: {file_path!r}")
        raise HTTPException(status_code=404, detail="File not found")

    if os.path.isfile(file_path):
        return FileResponse(file_path)

    raise HTTPException(status_code=404, detail="File not found")
