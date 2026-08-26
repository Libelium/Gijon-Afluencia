from fastapi import APIRouter, Response, Header, Query
from typing import Annotated
from app.core.config.logging import appLogging as logging

from aether_pylib.iota.iota_provision_payload import (
    DeviceProvisionPayload,
    ServiceProvisionPayload,
)
from aether_pylib.iota.delete_devices_request import DeleteDevicesRequest
from aether_pylib.iota.delete_devices_result import DeleteDevicesResult
from app.core.config.config import settings, iota_proxy
from http.client import HTTPException

iot_agent_router = APIRouter()


@iot_agent_router.get("/services/{entity_type}")
async def get_services(
    entity_type: str,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Get all services
    """
    try:
        return iota_proxy.get_services(entity_type, tenant, scope)
    except HTTPException as e:
        logging.error(f"Error getting services: {e}")
        return e.detail


@iot_agent_router.get("/services")
async def get_services(
    entity_type: Annotated[str, Query()] = None,
    device_type_code: Annotated[str, Query()] = None,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Get all services
    """
    try:
        return iota_proxy.get_services(entity_type, device_type_code, tenant, scope)
    except HTTPException as e:
        logging.error(f"Error getting services: {e}")
        return e.detail


@iot_agent_router.post("/provision/service")
async def provision_service(
    payload: ServiceProvisionPayload,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Provision a fiware service
    """
    try:
        iota_proxy.provision_service(payload, tenant, scope)
    except HTTPException as e:
        logging.error(f"Error provisioning service: {e}")
        return e.detail


@iot_agent_router.post("/provision/device")
async def provision_device_iota(
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
        return e.detail

@iot_agent_router.delete("/devices")
async def delete_devices(
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
        return e.detail
    