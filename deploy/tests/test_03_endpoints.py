"""
Stage 3 — public endpoints.

Hits each public hostname over HTTPS, from outside the cluster, exactly like a
user or a device would. Uses each service's own health endpoint where it has
one. This is the platform-level "is it reachable?" check; it is deliberately
agnostic about *how* traffic is routed (Ingress, Gateway API, cloud LB, …),
which is infrastructure the platform does not own.
"""

import pytest

from helpers.api import http_request
from helpers.config import config
from helpers.report import fail, require

SECTION = "Public endpoints"

ROUTE_NOT_MATCHED_ADVICE = (
    "Something answered on this hostname but no route matched it, so the request "
    "never reached the service. Your ingress/router does not have a rule for this "
    "host → service, or the public DNS name points at the wrong load balancer. "
    "Verify the routing rule for this hostname and that DNS resolves to the "
    "address fronting the cluster (these are infrastructure concerns, not part "
    "of the pid-gijon deployment itself)."
)


def _check_http(url: str, expected_statuses, service: str, *extra_advice: str):
    response = http_request("GET", url)

    body_snippet = (response.text or "")[:200].strip()
    if response.status_code == 404 and "404 page not found" in body_snippet:
        fail(
            f"{url} → 404 (gateway: no route matched)",
            ROUTE_NOT_MATCHED_ADVICE,
        )
    if response.status_code not in expected_statuses:
        fail(
            f"{url} → HTTP {response.status_code} (expected {expected_statuses})",
            f"Response: {body_snippet or '(empty)'}",
            f"Check the pod: kubectl logs -n {config.platform_namespace} deploy/{service}",
            *extra_advice,
        )


@pytest.mark.check(
    id="endpoint-api",
    title="Platform API reachable (web-back /api/hchk)",
    section=SECTION,
)
@pytest.mark.api
def test_api_endpoint():
    require("prereq-config")
    _check_http(
        f"{config.api_url}/api/hchk",
        {200},
        "web-back",
        "If web-back is not deployed yet, run the `webback` phase (enable web-back "
        "after the Keycloak setup).",
    )


@pytest.mark.check(
    id="endpoint-keycloak",
    title="Keycloak reachable and pid-gijon realm exists",
    section=SECTION,
)
@pytest.mark.api
def test_keycloak_endpoint():
    require("prereq-config")
    url = f"{config.keycloak_url}/realms/{config.keycloak_realm}/.well-known/openid-configuration"
    response = http_request("GET", url)
    body_snippet = (response.text or "")[:200].strip()
    if response.status_code == 404 and "404 page not found" in body_snippet:
        fail(f"{url} → 404 (gateway: no route matched)", ROUTE_NOT_MATCHED_ADVICE)
    if response.status_code == 404:
        fail(
            f"Keycloak answers, but realm '{config.keycloak_realm}' does not exist",
            "Create/import the realm and its clients — docs/06-post-install.md §6.1. "
            "The platform's Keycloak image may import it on first start; check "
            f"kubectl logs -n {config.platform_namespace} deploy/keycloak",
        )
    if response.status_code != 200:
        fail(
            f"{url} → HTTP {response.status_code}",
            f"Response: {body_snippet or '(empty)'}",
            f"Check Keycloak: kubectl logs -n {config.platform_namespace} deploy/keycloak — "
            "a crash here usually means the keycloak database or its credentials are "
            "wrong (stackgres.values.yaml vs pid-gijon-core.values.yaml must come from "
            "the same generator run).",
        )


@pytest.mark.check(
    id="endpoint-fiware",
    title="Device ingestion endpoint reachable (fiware-manager /hchk)",
    section=SECTION,
)
@pytest.mark.api
def test_fiware_manager_endpoint():
    require("prereq-config")
    _check_http(f"{config.fiware_manager_url}/hchk", {200}, "fiware-manager")


