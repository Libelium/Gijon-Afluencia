from http.client import HTTPException
from typing import List, Union
from aether_pylib.context_broker.create_entities_request import (
    CreateEntitiesRequest,
)
from aether_pylib.context_broker.update_entities_request import (
    UpdateEntitiesRequest,
)
from aether_pylib.context_broker.delete_entities_request import (
    DeleteEntitiesRequest,
)

from fastapi import APIRouter, Response, Header
from typing import Annotated
from app.core.config.config import context_broker_proxy
from app.core.config.logging import appLogging as logging
from app.core.config.config import settings

import requests

context_broker_router = APIRouter()


@context_broker_router.get("/dataTypes")
async def get_data_types(
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    List all data types
    """

    return context_broker_proxy.list_data_types(tenant, scope)


@context_broker_router.get("/platformTypeSubscriptions")
async def get_type_subscriptions(
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Get all types for which the platform has a subscription
    """

    return context_broker_proxy.list_type_subscriptions(tenant, scope)


@context_broker_router.patch("/platformTypeSubscriptions")
async def patch_entity_subscriptions(
    json_patch: List[dict],
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Patch the platform entity subscriptions
    """

    # path is ignored, and replace is not allowed
    new_entities = [patch["value"] for patch in json_patch if patch["op"] == "add"]
    delete_entities = [
        patch["value"] for patch in json_patch if patch["op"] == "remove"
    ]

    deleted_ok = context_broker_proxy.delete_type_subscriptions(
        delete_entities, tenant, scope
    )

    added_ok = context_broker_proxy.create_type_subscriptions(
        new_entities, tenant, scope
    )

    return {"deleted": deleted_ok, "added": added_ok}


@context_broker_router.get("/entities")
async def list_entities_by_type(
    types: str,
    response: Response,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
    limit: int | None = None,
    offset: int | None = None,
):
    """
    Get all entities of a given type
    """
    try:
        type_list = [] if types is None else types.split(",")
        return context_broker_proxy.list_entities_by_type(
            type_list, tenant, scope, limit=limit, offset=offset
        )

    except HTTPException as e:
        response.status_code = e.status_code
        return e.detail


@context_broker_router.post("/entities/update", status_code=207)
async def entities_update(
    request: UpdateEntitiesRequest,
    response: Response,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Entities update operation, following the UpdateEntitiesRequest schema
    """

    try:
        result = context_broker_proxy.update_entities(request, tenant, scope)

    except HTTPException as e:
        response.status_code = e.status_code

    if result is None:
        response.status_code = 500
        return "Internal server error"

    return result


@context_broker_router.post("/entities/create", status_code=207)
async def entities_update(
    request: CreateEntitiesRequest,
    response: Response,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Entities update operation, following the UpdateEntitiesRequest schema
    """

    try:
        result = context_broker_proxy.create_entities(request, tenant, scope)

    except HTTPException as e:
        response.status_code = e.status_code

    if result is None:
        response.status_code = 500
        return "Internal server error"

    return result


@context_broker_router.delete("/entities/delete", status_code=207)
async def entities_delete(
    request: DeleteEntitiesRequest,
    response: Response,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Entities delete operation, following the DeleteEntitiesRequest schema
    """

    try:
        result = context_broker_proxy.delete_entities(request, tenant, scope)
        logging.info(result)

    except HTTPException as e:
        response.status_code = e.status_code
    
    if result is None:
        response.status_code = 500
        return "Internal server error"

    return result


@context_broker_router.get("/entities/{urn}")
async def get_entity(
    urn: str,
    response: Response,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Get an entity from the Context Broker, it should return
    the most complete version of the entity
    """

    try:
        entity = context_broker_proxy.get_entity(urn, tenant, scope)
        if entity is None:
            # return 404
            response.status_code = 404
            return "Entity not found"
        return entity

    except HTTPException as e:
        response.status_code = e.status_code
        return e.detail


@context_broker_router.delete("/entities/{urn}/attrs/{attr_name}")
async def delete_entity_attribute(
    urn: str,
    attr_name: str,
    response: Response,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Delete an attribute from an entity in the Context Broker
    """
    result = context_broker_proxy.delete_entity_attribute(urn, attr_name, tenant, scope)

    if "error" in result:
        response.status_code = result.get("status", 500)
        return result

    return result
