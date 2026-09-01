from datetime import datetime

import dateutil.parser
import requests
from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import Response

import app.core.commands.commands as commands
import app.core.iota.utils as iota_utils
from app.core.config.config import settings
from app.core.config.logging import appLogging as log
from app.core.parser.json_flattener import JsonFlattener

router = APIRouter()

_flattener = JsonFlattener()


# SEC-044. This is the device ingestion endpoint (the public
# `command-proxy/iot/json?i=<device>&k=<apikey>` path). The `k` query parameter
# IS the device's authentication: it is the per-device apikey of the IoT Agent
# service group, and the IoT Agent validates it southbound before accepting any
# measure. We deliberately do NOT add a separate shared bearer token here — a
# device sends its apikey in `k`, never an extra header, so gating this route on
# one would reject every real device and break ingestion. The apikey travelling
# in the query string is the credential by design.
@router.post("/{resource:path}", status_code=200)
@router.put("/{resource:path}", status_code=200)
def redirect(
    resource: str,
    # COD-088. These were the bare names `i`, `k` and `getCmd`. They are renamed
    # for readability but keep their wire names through `alias`, because they are
    # the IoT Agent's own query-string contract and devices send them literally.
    device_id: str = Query(alias="i"),
    api_key: str = Query(alias="k"),
    get_cmd: int = Query(default=0, alias="getCmd"),
    flatten_depth: int | None = None,
    payload=Body(...),
):
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

        log.info(
            f"Redirecting command to {device_id} and {api_key}, with payload: {tp}"
        )

        response = requests.post(
            f"{settings.IOTA_SOUTH_SERVICE}/{resource}",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            params={
                "k": api_key,
                "i": device_id,
            },
            json=tp,
            timeout=settings.HTTP_TIMEOUT,
        )

        if response.status_code >= 400:
            log.error(
                f"Error redirecting command to {device_id} and {api_key} with "
                f"payload: {tp}, status: {response.status_code}, "
                f"response: {response.text}"
            )

    if get_cmd > 0:
        pending_cmds = commands.get_ik_pending_commands(device_id, api_key)

        log.info(f"Pending commands for {device_id} and {api_key}: {pending_cmds}")

        if pending_cmds and len(pending_cmds) > 0:
            return pending_cmds

    return Response(status_code=204)
