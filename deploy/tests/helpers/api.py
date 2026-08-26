"""
Platform API client for the verification suite.

Adapted from the platform integration-test suite (auth, devices, entities,
commands, timeseries), trimmed to the flows this installer can verify and
hardened for first-install diagnostics: every call has a timeout, TLS
verification is configurable (new installs often run self-signed), and errors
are classified into actionable advice for the final report.
"""

import random
import time
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from .config import config
from .report import CheckFailure

if not config.tls_verify:
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")


@dataclass
class EntityIdentifier:
    urn: str
    tenant: str
    scope: str = "/"


@dataclass
class Device:
    id: Any
    serial: str
    main_entity_id: Optional[int] = None
    main_entity: Optional[EntityIdentifier] = None
    raw_response: Optional[dict] = None


@dataclass
class SendDataResult:
    success: bool
    status_code: int
    body: str


def _is_success(status_code: int) -> bool:
    return 200 <= status_code < 300


def http_request(method: str, url: str, **kwargs) -> requests.Response:
    """Perform an HTTP request with the suite's timeout/TLS settings.

    Network-level failures are converted into CheckFailure with advice, so any
    check using the client reports a clear diagnosis instead of a traceback.
    """
    kwargs.setdefault("timeout", config.http_timeout)
    kwargs.setdefault("verify", config.tls_verify)
    try:
        return requests.request(method, url, **kwargs)
    except requests.exceptions.SSLError as exc:
        raise CheckFailure(
            f"TLS error calling {url}: {exc}",
            [
                "The certificate served on this hostname is not trusted by this machine.",
                "If you use a self-signed certificate, set TLS_VERIFY=false in tests.env.",
                "To fix properly, serve a certificate valid for this hostname from "
                "whatever terminates TLS in your infrastructure.",
            ],
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise CheckFailure(
            f"Cannot connect to {url}",
            [
                "DNS may not resolve, or it may point at the wrong IP, or the load "
                "balancer is not reachable from this machine.",
                "Confirm the public DNS name resolves to the address fronting the "
                "cluster (this is infrastructure, not part of the pid-gijon deployment).",
                f"Underlying error: {exc}",
            ],
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise CheckFailure(
            f"Timed out after {config.http_timeout}s calling {url}",
            [
                "The endpoint accepted the connection but did not answer in time.",
                "Check the backing pod's logs and readiness: kubectl get pods -n pid-gijon",
            ],
        ) from exc


# --- authentication ----------------------------------------------------------

def login() -> str:
    """Authenticate against web-back; returns a bearer token or raises CheckFailure."""
    if not config.admin_username or not config.admin_password:
        raise CheckFailure(
            "ADMIN_USERNAME / ADMIN_PASSWORD are not set",
            ["Fill them in environments/<name>/tests.env with a platform admin login."],
        )

    url = f"{config.api_url}/api/V1/login"
    response = http_request(
        "POST",
        url,
        json={"username": config.admin_username, "password": config.admin_password},
        headers={"Content-Type": "application/json"},
    )

    if response.status_code == 401:
        raise CheckFailure(
            f"Login rejected (401) for user '{config.admin_username}'",
            [
                "The platform does not recognise these credentials.",
                "Verify the user exists in the Keycloak 'pid-gijon' realm and is a "
                "platform admin (docs/06-post-install.md §6.1).",
                "If you created a different admin user, set ADMIN_USERNAME / "
                "ADMIN_PASSWORD in environments/<name>/tests.env.",
                "Also confirm KEYCLOAK_PUBLIC_KEY / KEYCLOAK_CLIENT_SECRET were "
                "filled in after the Keycloak setup (they must not be "
                "REPLACE_AFTER_KEYCLOAK_SETUP) and web-back was re-deployed.",
            ],
        )
    if response.status_code == 404:
        raise CheckFailure(
            "Login endpoint returned 404 — the request did not reach web-back",
            [
                "Something answered but no route matched, so the request never "
                "reached web-back. Check your ingress/router rule for the API "
                "hostname → web-back, and that DNS points at the right load balancer.",
                "See the 'Public endpoints' check above — it isolates the same issue.",
            ],
        )
    if not _is_success(response.status_code):
        raise CheckFailure(
            f"Login failed with HTTP {response.status_code}",
            [
                f"Response body: {response.text[:300]}",
                "Inspect web-back: kubectl logs -n pid-gijon deploy/web-back",
                "5xx during first install often means the Keycloak realm/clients are "
                "not configured yet (docs/06-post-install.md).",
            ],
        )

    body = response.json()
    token = (
        body.get("token")
        or body.get("access_token")
        or body.get("data", {}).get("token")
    )
    if not token:
        raise CheckFailure(
            "Login succeeded but no token was found in the response",
            [f"Response keys: {list(body)[:10]}"],
        )
    return token


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}


# --- devices ------------------------------------------------------------------


def get_device_by_serial(token: str, serial: str) -> Device:
    """
    Resuelve un dispositivo ya aprovisionado a partir de su serial.

    La API de gestión dejó de exponer el alta y la baja de dispositivos, así que la
    batería ya no crea uno desechable: se le indica uno existente con
    TEST_DEVICE_SERIAL y solo lee. No modifica nada, de modo que es seguro apuntarla
    a un dispositivo real en producción.
    """
    url = f"{config.api_url}/api/V1/devices/paginate"
    payload = {"filters": {"serial": serial}, "page": 1, "per_page": 1}

    response = http_request("POST", url, json=payload, headers=_auth_headers(token))
    if not _is_success(response.status_code):
        raise CheckFailure(
            f"Could not query devices (HTTP {response.status_code})",
            [
                f"Response body: {response.text[:300]}",
                "Check web-back logs: "
                f"kubectl logs -n {config.platform_namespace} deploy/web-back",
            ],
        )

    rows = (response.json() or {}).get("data") or []
    match = next((r for r in rows if str(r.get("serial", "")).upper() == serial.upper()), None)
    if match is None:
        raise CheckFailure(
            f"No device with serial '{serial}' in this installation",
            [
                "TEST_DEVICE_SERIAL must name a device that already exists and has a "
                "main entity provisioned.",
                "List the available ones with the platform UI or "
                "POST /api/V1/devices/paginate.",
            ],
        )

    main_entity_data = match.get("main_entity") or {}
    main_entity = None
    if main_entity_data:
        main_entity = EntityIdentifier(
            urn=main_entity_data.get("urn", ""),
            tenant=main_entity_data.get("tenant", ""),
            scope=main_entity_data.get("scope", "/"),
        )

    if main_entity is None or not main_entity.urn:
        raise CheckFailure(
            f"Device '{serial}' has no main entity provisioned",
            [
                "The data-path checks need a device whose main entity exists in the "
                "context broker.",
                f"Check: kubectl logs -n {config.platform_namespace} deploy/fiware-manager",
            ],
        )

    return Device(
        id=match.get("id"),
        serial=match.get("serial", serial),
        main_entity_id=main_entity_data.get("id"),
        main_entity=main_entity,
        raw_response=match,
    )


def discover_api_key(token: str, device: Device) -> str:
    """Best-effort discovery of the device-type API key when DATA_API_KEY is unset.

    Looks for an api_key-ish field in the device payload the platform returned.
    Returns "" when nothing is found, and the caller falls back to the IoT Agent
    admin API (see kube.discover_data_api_key).
    """
    candidates = [device.raw_response or {}]

    def search(node: Any) -> str:
        if isinstance(node, dict):
            for key, value in node.items():
                normalized = key.lower().replace("-", "_")
                if normalized in ("api_key", "apikey", "data_api_key") and isinstance(value, str) and value:
                    return value
            for value in node.values():
                found = search(value)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = search(item)
                if found:
                    return found
        return ""

    for candidate in candidates:
        found = search(candidate)
        if found:
            return found
    return ""


# --- device data (HTTP ingestion via fiware-manager) --------------------------

def send_data(
    serial: str, data: Dict[str, Any], api_key: str, get_cmd: int = 0
) -> SendDataResult:
    url = (
        f"{config.fiware_manager_url}/api/v1/command-proxy/iot/json"
        f"?i={serial}&k={api_key}&getCmd={get_cmd}"
    )
    response = http_request(
        "POST", url, json=data, headers={"Content-Type": "application/json"}
    )
    return SendDataResult(
        success=_is_success(response.status_code),
        status_code=response.status_code,
        body=response.text,
    )


def generate_random_temperature() -> float:
    return round(random.uniform(10.0, 40.0), 2)


# --- entities ------------------------------------------------------------------

def get_entity(token: str, entity_id: int) -> Optional[dict]:
    url = f"{config.api_url}/api/V1/entities/{entity_id}"
    response = http_request("GET", url, headers={"Authorization": f"Bearer {token}"})
    if not _is_success(response.status_code):
        return None
    return response.json()


def read_entity_properties(token: str, entity: EntityIdentifier) -> Optional[List[dict]]:
    url = f"{config.api_url}/api/V1/realtime/entities/{entity.urn}"
    headers = {
        "Authorization": f"Bearer {token}",
        "tenant": entity.tenant,
        "scope": entity.scope,
    }
    response = http_request("GET", url, headers=headers)
    if not _is_success(response.status_code):
        return None
    body = response.json()
    return body if isinstance(body, list) else None


def find_property_value(properties: List[dict], property_name: str) -> Optional[Any]:
    capitalized = property_name.capitalize()
    for prop in properties:
        if prop.get("id") == property_name or prop.get("name") == capitalized:
            return prop.get("value")
    return None


def wait_for_property_in(
    token: str,
    entity: EntityIdentifier,
    property_name: str,
    expected_values: List[float],
    attempts: Optional[int] = None,
    wait_seconds: Optional[float] = None,
) -> Tuple[bool, Optional[Any]]:
    """Poll until the property matches ANY of expected_values (tolerance 0.01).

    Used to verify the entity reflects *something the device sent* without
    depending on which of several rapid, unsynchronised updates the async
    pipeline settles on last (that ordering is not a platform guarantee).
    """
    attempts = attempts or config.propagation_attempts
    wait_seconds = wait_seconds if wait_seconds is not None else config.propagation_interval
    targets = [float(value) for value in expected_values]
    last_value = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(wait_seconds)
        properties = read_entity_properties(token, entity)
        if properties is None:
            continue
        last_value = find_property_value(properties, property_name)
        if isinstance(last_value, (int, float)) and any(
            abs(float(last_value) - target) < 0.01 for target in targets
        ):
            return True, last_value
    return False, last_value


# --- commands -------------------------------------------------------------------

def send_command(token: str, main_entity_id: int, commands: Dict[str, Any]) -> Tuple[bool, str]:
    url = f"{config.api_url}/api/V1/entities/{main_entity_id}/sendCommands"
    response = http_request("POST", url, json=commands, headers=_auth_headers(token))
    if _is_success(response.status_code):
        return True, ""
    return False, f"HTTP {response.status_code}: {response.text[:200]}"


# --- timeseries -----------------------------------------------------------------

def query_timeseries(
    token: str,
    device_urn: str,
    measure_id: str,
    tenant: str,
    start: datetime,
    end: datetime,
    limit: int,
) -> Optional[List[dict]]:
    url = f"{config.api_url}/api/V1/timeseries"
    payload = [
        {
            "device_ids": [device_urn],
            "measure_ids": [measure_id],
            "options": {
                "query_id": "installer-verification",
                "order": "desc",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "limit": limit,
                "tenant": tenant,
                "scope": "/",
            },
        }
    ]
    response = http_request(
        "POST", url, json=payload, headers=_auth_headers(token), timeout=30
    )
    if not _is_success(response.status_code):
        return None
    body = response.json()
    return body if isinstance(body, list) else None


def extract_timeseries_values(
    response: List[dict], device_urn: str, measure_id: str
) -> List[dict]:
    for result in response or []:
        for series in result.get("time_series", []):
            if (
                series.get("device_id") == device_urn
                and series.get("measure_id") == measure_id
            ):
                return series.get("values", [])
    return []
