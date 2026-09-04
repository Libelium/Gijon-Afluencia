from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query

from aether_pylib.iota.iota_provision_payload import (
    DeviceProvisionPayload,
    ServiceProvisionPayload,
)
from aether_pylib.iota.delete_devices_request import DeleteDevicesRequest
from app.core.config.config import settings, iota_proxy
from app.core.config.logging import appLogging as logging

# COD-076. This module used to do `from http.client import HTTPException`.
# http.client.HTTPException is the base class of the stdlib HTTP client errors;
# it is unrelated to fastapi.HTTPException, which is what `iota_proxy` actually
# raises (see IOTAJsonLdProxy.get_services / provision_service / ...). So none of
# the `except HTTPException` blocks below could ever match, and on top of that
# http.client.HTTPException carries neither `.status_code` nor `.detail`, so the
# handler bodies would have raised AttributeError had they ever run.
#
# Note on the fix: the blocks now log and re-raise instead of `return e.detail`.
# Returning the detail would send the payload with HTTP 200, because these
# handlers never set a status code - i.e. a "corrected" import that kept the
# original bodies would have turned every upstream 404/400 into a 200. Letting
# the exception propagate keeps FastAPI's own handler, which renders the right
# status, while still recording the error in the log as intended.

iot_agent_router = APIRouter()


@iot_agent_router.get("/services/{entity_type}")
def get_services_by_entity_type(
    entity_type: str,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Get the services registered for a single entity type
    """
    # COD-077. Renamed from `get_services`, which was defined twice in this
    # module. Both routes were and are reachable (FastAPI binds the function
    # object at decoration time), but the duplicate name shadowed the first
    # definition at module level and made `url_path_for("get_services")`
    # ambiguous.
    #
    # The rename also uncovered a real defect: this handler called the proxy
    # with three positional arguments while IOTAJsonLdProxy.get_services takes
    # four (entity_type, device_type_code, tenant, scope). `tenant` was landing
    # in `device_type_code`, `scope` in `tenant`, and `scope` was left unbound,
    # so every call raised
    #   TypeError: IOTAJsonLdProxy.get_services() missing 1 required positional
    #   argument: 'scope'
    # and the endpoint answered 500 unconditionally. Arguments are passed by
    # keyword now so the mismatch cannot come back silently.
    try:
        return iota_proxy.get_services(
            entity_type=entity_type,
            device_type_code=None,
            tenant=tenant,
            scope=scope,
        )
    except HTTPException as e:
        logging.error(f"Error getting services for entity type {entity_type}: {e}")
        raise


@iot_agent_router.get("/services")
def get_services(
    entity_type: Annotated[str, Query()] = None,
    device_type_code: Annotated[str, Query()] = None,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Get all services, optionally filtered by entity type and device type code
    """
    try:
        return iota_proxy.get_services(
            entity_type=entity_type,
            device_type_code=device_type_code,
            tenant=tenant,
            scope=scope,
        )
    except HTTPException as e:
        logging.error(f"Error getting services: {e}")
        raise


@iot_agent_router.post("/provision/service")
def provision_service(
    payload: ServiceProvisionPayload,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Provision a fiware service
    """
    try:
        return iota_proxy.provision_service(payload, tenant, scope)
    except HTTPException as e:
        logging.error(f"Error provisioning service: {e}")
        raise


@iot_agent_router.post("/provision/device")
def provision_device_iota(
    payload: DeviceProvisionPayload,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Provision a new device in the IOTA
    """
    try:
        return iota_proxy.provision_device(payload, tenant, scope)
    except HTTPException as e:
        logging.error(f"Error provisioning device: {e}")
        raise


@iot_agent_router.delete("/devices")
def delete_devices(
    devices: DeleteDevicesRequest,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Delete devices from the IOTA
    """
    try:
        return iota_proxy.delete_devices(devices, tenant, scope)
    except HTTPException as e:
        logging.error(f"Error deleting devices: {e}")
        raise
