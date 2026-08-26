from inspect import Parameter, signature
from typing import Any

from config.logging import appLogging as logging
from config.celery import app as celery_app
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, FileResponse
from schemas.context_broker_notification_schema import ContextBrokerNotification
from schemas.fiware_subscription_schema import TypeSubscriptionMessage
from schemas.task_request_schema import TaskRequest
from tasks.sync import fiware_orion_subscription_job, fiware_type_subscription_job
from fastapi.middleware.cors import CORSMiddleware
import os
from config.config import settings


application = FastAPI(
    docs_url="/docs" if settings.ENABLE_SWAGGER else None,
    redoc_url="/redoc" if settings.ENABLE_SWAGGER else None,
    openapi_url="/openapi.json" if settings.ENABLE_SWAGGER else None,
)

# Configure CORS
origins = [
    "*",
]

application.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@application.get("/hchk")
def health_check():
    return "OK"


@application.post("/orion-ld/subscription", status_code=204)
async def subscription(request: Request):
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


@application.post("/publish", status_code=204)
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

    # get the task parameters
    task_params = request.params

    task = celery_app.tasks[task_name]

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


# receives a url and a method and sends a request to it
@application.post("/test-connection", status_code=200)
def test_connection(request: TaskRequest) -> None:
    import requests

    url = request.params.get("url", None)
    method = request.params.get("method", "GET")
    headers = request.params.get("headers", {})
    body = request.params.get("body", {})
    timeout = request.params.get("timeout", 5)

    try:
        response = requests.request(
            method, url, headers=headers, json=body, timeout=timeout
        )
        return response.json()
    except Exception as e:
        logging.error(e)
        return {"error": str(e)}


# FastAPI endpoint to serve HLS playlist and segments
@application.get("/stream/{pipeline_id}/{entity_id}/{file}")
async def get_hls_file(pipeline_id: int, entity_id: int, file: str):
    logging.info(
        f"Requesting file for pipeline_id: {pipeline_id}, entity_id: {entity_id}, output_type: {file}"
    )
    filename = f"pipeline_{pipeline_id}/entity_{entity_id}/{file}"
    file_path = os.path.join(settings.STREAMING_OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="File not found")
