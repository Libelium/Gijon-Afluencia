"""
Regression tests for COD-076 and COD-077.

The two proxy route modules had no test coverage at all, which is how a wrong
`HTTPException` import, two pairs of duplicate handler names, an arity mismatch
against the IOTA proxy and three `UnboundLocalError` fall-throughs all survived.

These tests drive the handlers directly with `asyncio.run` instead of going
through `fastapi.testclient.TestClient`, so they need no HTTP client dependency
beyond what the project already declares.
"""

import asyncio
import inspect
from collections import Counter
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import HTTPException, Response

from app.api.v1.routes import context_broker, iot_agent
from app.core.iota.iota_proxy.iota_json_proxy.iota_json_ld_proxy import IOTAJsonLdProxy


# --------------------------------------------------------------------------- #
# COD-076 - the routers must catch fastapi.HTTPException, not http.client's
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("module", [context_broker, iot_agent])
def test_http_exception_is_the_fastapi_one(module):
    """
    `from http.client import HTTPException` silently disabled every `except`
    block in these modules: it is an unrelated class, and it carries neither
    `.status_code` nor `.detail`.
    """
    assert module.HTTPException is HTTPException
    assert module.HTTPException.__module__ == "fastapi.exceptions"


# --------------------------------------------------------------------------- #
# COD-077 - handler names must be unique within a router
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "router",
    [context_broker.context_broker_router, iot_agent.iot_agent_router],
)
def test_no_duplicate_handler_names(router):
    """
    Duplicate function names do not make a route unreachable - FastAPI binds the
    function object when the decorator runs - but they shadow the first
    definition at module level and make `url_path_for` ambiguous.
    """
    names = [route.name for route in router.routes]
    duplicated = [name for name, count in Counter(names).items() if count > 1]
    assert duplicated == [], f"duplicate handler names: {duplicated}"


def test_every_route_still_registered():
    """Renaming the duplicates must not drop any path."""
    paths = {(route.path, tuple(sorted(route.methods))) for route in
             context_broker.context_broker_router.routes}
    assert ("/entities/update", ("POST",)) in paths
    assert ("/entities/create", ("POST",)) in paths

    iot_paths = {route.path for route in iot_agent.iot_agent_router.routes}
    assert {"/services", "/services/{entity_type}"} <= iot_paths


# --------------------------------------------------------------------------- #
# The arity bug uncovered while fixing COD-077
# --------------------------------------------------------------------------- #
def test_get_services_by_entity_type_matches_the_proxy_signature():
    """
    `GET /services/{entity_type}` used to call the proxy with three positional
    arguments while IOTAJsonLdProxy.get_services takes four, so it raised
    `TypeError: ... missing 1 required positional argument: 'scope'` on every
    single request. This binds the recorded call against the real signature so
    the mismatch cannot come back.
    """
    proxy = MagicMock()
    with patch.object(iot_agent, "iota_proxy", proxy):
        asyncio.run(
            iot_agent.get_services_by_entity_type(
                entity_type="AirQualityObserved", tenant="tenantA", scope="/scopeA"
            )
        )

    proxy.get_services.assert_called_once()
    args, kwargs = proxy.get_services.call_args
    # Must bind cleanly against the concrete implementation.
    inspect.signature(IOTAJsonLdProxy.get_services).bind(
        MagicMock(), *args, **kwargs
    )
    assert kwargs == {
        "entity_type": "AirQualityObserved",
        "device_type_code": None,
        "tenant": "tenantA",
        "scope": "/scopeA",
    }


def test_iot_agent_reraises_http_exception_instead_of_returning_200():
    """
    The original bodies did `return e.detail` without touching the status code,
    so an upstream 404 would have been served as HTTP 200 once the import was
    corrected. Re-raising keeps FastAPI's own renderer and the right status.
    """
    proxy = MagicMock()
    proxy.get_services.side_effect = HTTPException(
        status_code=404, detail="Service not found"
    )
    with patch.object(iot_agent, "iota_proxy", proxy):
        with pytest.raises(HTTPException) as excinfo:
            asyncio.run(
                iot_agent.get_services_by_entity_type(
                    entity_type="Nope", tenant="tenantA", scope="/scopeA"
                )
            )
    assert excinfo.value.status_code == 404


# --------------------------------------------------------------------------- #
# The UnboundLocalError fall-through in the /entities/* handlers
# --------------------------------------------------------------------------- #
def _http_error(status_code: int) -> requests.exceptions.HTTPError:
    upstream = requests.Response()
    upstream.status_code = status_code
    return requests.exceptions.HTTPError("upstream refused", response=upstream)


@pytest.mark.parametrize(
    "handler_name, proxy_method",
    [
        ("entities_update", "update_entities"),
        ("entities_create", "create_entities"),
        ("entities_delete", "delete_entities"),
    ],
)
def test_entities_handlers_do_not_fall_through_with_unbound_result(
    handler_name, proxy_method
):
    """
    `result` is assigned inside the `try`; the old `except` only set
    `response.status_code` and fell through to `if result is None`, which raised
    UnboundLocalError. Each handler must now return the upstream status instead.
    """
    proxy = MagicMock()
    getattr(proxy, proxy_method).side_effect = _http_error(422)
    response = Response()

    with patch.object(context_broker, "context_broker_proxy", proxy):
        body = asyncio.run(
            getattr(context_broker, handler_name)(
                request=MagicMock(), response=response, tenant="t", scope="/s"
            )
        )

    assert response.status_code == 422
    assert body["status"] == 422


@pytest.mark.parametrize(
    "handler_name, proxy_method",
    [
        ("entities_update", "update_entities"),
        ("entities_create", "create_entities"),
        ("entities_delete", "delete_entities"),
    ],
)
def test_entities_handlers_map_unreachable_broker_to_502(handler_name, proxy_method):
    """A connection error carries no response, so it must become 502, not 500."""
    proxy = MagicMock()
    getattr(proxy, proxy_method).side_effect = requests.exceptions.ConnectionError(
        "orion-ld unreachable"
    )
    response = Response()

    with patch.object(context_broker, "context_broker_proxy", proxy):
        body = asyncio.run(
            getattr(context_broker, handler_name)(
                request=MagicMock(), response=response, tenant="t", scope="/s"
            )
        )

    assert response.status_code == 502
    assert body["status"] == 502


def test_get_entity_maps_upstream_status():
    proxy = MagicMock()
    proxy.get_entity.side_effect = _http_error(503)
    response = Response()

    with patch.object(context_broker, "context_broker_proxy", proxy):
        body = asyncio.run(
            context_broker.get_entity(
                urn="urn:ngsi-ld:Device:1", response=response, tenant="t", scope="/s"
            )
        )

    assert response.status_code == 503
    assert body["status"] == 503


def test_list_entities_by_type_maps_upstream_status():
    proxy = MagicMock()
    proxy.list_entities_by_type.side_effect = _http_error(400)
    response = Response()

    with patch.object(context_broker, "context_broker_proxy", proxy):
        body = asyncio.run(
            context_broker.list_entities_by_type(
                types="Device", response=response, tenant="t", scope="/s"
            )
        )

    assert response.status_code == 400
    assert body["status"] == 400
