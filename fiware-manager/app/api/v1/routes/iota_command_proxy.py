from fastapi import APIRouter, Body
from app.core.config.logging import appLogging as log
import app.core.commands.commands as commands
import requests
from app.core.config.config import settings
from fastapi.responses import Response
import app.core.iota.utils as iota_utils
from app.core.parser.json_flattener import JsonFlattener
import dateutil.parser
from datetime import datetime

router = APIRouter()

_flattener = JsonFlattener()


@router.post("/{resource:path}", status_code=200)
@router.put("/{resource:path}", status_code=200)
def redirect(resource, i, k, getCmd=0, flatten_depth: int | None = None, payload=Body(...)):
    """
    Redirects the command to the iot agent and checks if there was
    any command pending for the device.
    It also translates some attributes to TimeInstant because NGSI-LD
    does not support the TimeInstant attribute in translation expressions.
    If `flatten_depth` is not None, dissolves that number of levels of nested dicts in the payload,

    Declared sync on purpose: everything below blocks (requests to the IoT Agent,
    pymongo for the pending commands). As `async def` it ran straight on the
    event loop and starved the worker heartbeat; FastAPI runs a sync handler in
    the threadpool instead.
    """

    if isinstance(payload, dict):
        payload = [payload]

    translation_map = {key: "TimeInstant" for key in settings.TIMESTAMP_ATTRS}

    for p in payload:
        if flatten_depth is not None:
            p = _flattener.flatten(p, max_depth=flatten_depth)
        tp = iota_utils.attr_translation(p, translation_map, append_mode=True)
        ts = tp.get("TimeInstant", None)
        if ts and isinstance(ts, int):
            tp["TimeInstant"] = dateutil.parser.parse(
                datetime.fromtimestamp(ts).isoformat(), ignoretz=False
            ).isoformat()

        log.info(f"Redirecting command to {i} and {k}, with payload: {tp}")

        respone = requests.post(
            f"{settings.IOTA_SOUTH_SERVICE}/{resource}",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            params={
                "k": k,
                "i": i,
            },
            json=tp,
            timeout=settings.HTTP_TIMEOUT,
        )

        if respone.status_code >= 400:
            log.error(
                f"Error redirecting command to {i} and {k} with payload: {tp}, "
                f"status: {respone.status_code}, response: {respone.text}"
            )

    if int(getCmd) > 0:
        pending_cmds = commands.get_ik_pending_commands(i, k)

        log.info(f"Pending commands for {i} and {k}: {pending_cmds}")

        if pending_cmds and len(pending_cmds) > 0:
            return pending_cmds

    return Response(status_code=204)
