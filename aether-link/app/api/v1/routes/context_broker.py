from typing import List
from aether_pylib.context_broker.create_entities_request import (
    CreateEntitiesRequest,
)
from aether_pylib.context_broker.update_entities_request import (
    UpdateEntitiesRequest,
)
from aether_pylib.context_broker.delete_entities_request import (
    DeleteEntitiesRequest,
)

from fastapi import APIRouter, Response, Header, HTTPException
from typing import Annotated
from app.core.config.config import context_broker_proxy
from app.core.config.logging import appLogging as logging
from app.core.config.config import settings

import requests

# COD-076. This module used to do `from http.client import HTTPException`, which
# is the stdlib HTTP *client* base exception and has neither `.status_code` nor
# `.detail`. Every `except HTTPException` below was therefore dead code.
#
# Fixing the import alone is not enough, because nothing in the Context Broker
# path raises fastapi.HTTPException either: OrionLdProxy delegates to
# `crud/entity_crud.py`, which signals upstream failures with
# `requests.exceptions.HTTPError` (and network failures with the other
# `requests.exceptions.RequestException` subclasses). So the handlers now catch
# what is actually thrown and translate it into a proper status code.

# The handlers are synchronous on purpose: they talk to the broker with blocking
# `requests`, so FastAPI runs them in its thread pool instead of the event loop.
context_broker_router = APIRouter()


def _upstream_error(exc: requests.exceptions.RequestException, action: str) -> tuple:
    """
    Translate a failure coming from the Context Broker into (status_code, body).

    A response-bearing error (HTTPError) keeps the upstream status; a bare
    connection/timeout error becomes 502, which is what "the broker could not be
    reached" means to our own callers.
    """
    upstream = getattr(exc, "response", None)
    status_code = upstream.status_code if upstream is not None else 502
    logging.error(f"Error {action}: {status_code} - {exc}")
    return status_code, {"error": str(exc), "status": status_code}


@context_broker_router.get("/dataTypes")
def get_data_types(
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    List all data types
    """

    return context_broker_proxy.list_data_types(tenant, scope)


@context_broker_router.get("/platformTypeSubscriptions")
def get_type_subscriptions(
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Get all types for which the platform has a subscription
    """

    return context_broker_proxy.list_type_subscriptions(tenant, scope)


@context_broker_router.patch("/platformTypeSubscriptions")
def patch_entity_subscriptions(
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
def list_entities_by_type(
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

    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        response.status_code, body = _upstream_error(e, "listing entities by type")
        return body


@context_broker_router.post("/entities/update", status_code=207)
def entities_update(
    request: UpdateEntitiesRequest,
    response: Response,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Entities update operation, following the UpdateEntitiesRequest schema
    """

    # The `except` branch used to only assign `response.status_code` and fall
    # through to `if result is None`, where `result` was still unbound because
    # it is assigned inside the `try`. That path raised UnboundLocalError and
    # answered 500 with a stack trace instead of the intended error. Returning
    # from the handler removes the fall-through entirely.
    try:
        result = context_broker_proxy.update_entities(request, tenant, scope)

    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        response.status_code, body = _upstream_error(e, "updating entities")
        return body

    if result is None:
        response.status_code = 500
        return "Internal server error"

    return result


@context_broker_router.post("/entities/create", status_code=207)
def entities_create(
    request: CreateEntitiesRequest,
    response: Response,
    tenant: Annotated[str, Header()] = settings.DEFAULT_TENANT,
    scope: Annotated[str | None, Header()] = settings.DEFAULT_SCOPE,
):
    """
    Entities create operation, following the CreateEntitiesRequest schema
    """

    # COD-077. This handler was also called `entities_update`, shadowing the
    # /entities/update one above at module level. Both routes were reachable -
    # FastAPI captures the function object when the decorator runs - but the
    # duplicate name made the module-level symbol and `url_path_for` ambiguous.
    try:
        result = context_broker_proxy.create_entities(request, tenant, scope)

    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        response.status_code, body = _upstream_error(e, "creating entities")
        return body

    if result is None:
        response.status_code = 500
        return "Internal server error"

    return result


@context_broker_router.delete("/entities/delete", status_code=207)
def entities_delete(
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

    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        response.status_code, body = _upstream_error(e, "deleting entities")
        return body

    if result is None:
        response.status_code = 500
        return "Internal server error"

    return result


@context_broker_router.get("/entities/{urn}")
def get_entity(
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

    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        response.status_code, body = _upstream_error(e, f"getting entity {urn}")
        return body


@context_broker_router.delete("/entities/{urn}/attrs/{attr_name}")
def delete_entity_attribute(
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
