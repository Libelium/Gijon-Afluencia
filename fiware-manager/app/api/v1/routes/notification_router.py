from typing import Annotated
from fastapi import APIRouter, Body, Header
from app.core.config.logging import appLogging as log
import app.core.commands.commands as commands

router = APIRouter()


@router.post("/command/{serial}", status_code=200)
def notify(
    serial,
    fiware_service: Annotated[str, Header()],  # the tenant
    fiware_servicepath: Annotated[str | None, Header()],  # the scope
    payload=Body(...),
):
    # Sync on purpose — see the note in iota_command_proxy.redirect.
    log.info(
        f"Received {payload} commands for {serial}, service: {fiware_service}, servicepath: {fiware_servicepath}"
    )

    # just in case the serial is lowercase
    serial = serial.upper()

    commands.add_new_command(
        device_serial=serial,
        tenant=fiware_service,
        scope=fiware_servicepath,
        payload=payload,
    )

    return {
        command: {
            "status": "PENDING",
            "value": value,
        }
        for command, value in payload.items()
    }
