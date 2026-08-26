"""
Stage 5 — device lifecycle (adapted from the platform integration-test suite).

Walks the full IoT path a real device takes:

  create device (admin API) → send measurements (HTTP via fiware-manager /
  iot-agent-json) → entity reflects the data (orion-ld pipeline) → command
  roundtrip (API → device polling with getCmd=1) → delete device

Each step is its own check so the report pinpoints which hop of the pipeline
broke. LoRaWAN/MQTT paths are intentionally out of scope for this installer.
"""

import json

import pytest

from helpers import api, kube, report, session
from helpers.config import config
from helpers.report import fail, require

SECTION = "Device lifecycle (IoT data path)"

DATA_SENDS = 2

# Temperatures pushed by test_send_data, consumed by the entity check.
_SENT_TEMPERATURES = []


def _require_api_key() -> str:
    if session.data_api_key:
        return session.data_api_key
    message = "no DATA_API_KEY available — the device data path cannot be verified"
    advice = (
        "On a standard install the suite auto-discovers it after creating the "
        "test device; this usually means kubectl could not reach the IoT Agent, "
        "or your installation is non-standard.",
        "Set DATA_API_KEY in environments/<name>/tests.env (tests/README.md, "
        "'Obtaining DATA_API_KEY and TENANT'), or set REQUIRE_DATA_PATH=false to "
        "treat the data path as optional.",
    )
    # Default is strict: device-create already succeeded, so the platform is up
    # and auth works — being unable to push data is a real failure, not a skip.
    if config.require_data_path:
        fail(message, *advice)
    pytest.skip(message + " (REQUIRE_DATA_PATH=false)")


@pytest.mark.check(
    id="device-create",
    title="Resolve the device under test",
    section=SECTION,
)
@pytest.mark.api
def test_resolve_device():
    require("auth-login")
    if not config.device_serial:
        pytest.skip(
            "TEST_DEVICE_SERIAL is not set. The management API no longer exposes "
            "device provisioning, so this suite cannot create a throwaway device: "
            "point it at one that already exists (see tests/README.md)."
        )

    session.device = api.get_device_by_serial(session.token, config.device_serial)

    if not session.device.main_entity or not session.device.main_entity.urn:
        fail(
            "Device was created but has no main entity",
            "fiware-manager could not provision the device's entity. Check: "
            f"kubectl logs -n {config.platform_namespace} deploy/fiware-manager and "
            f"kubectl logs -n {config.platform_namespace} deploy/orion-ld",
        )

    # Resolve the API key for the data-path checks, in order of preference:
    #   1. explicit DATA_API_KEY from tests.env (works without cluster access)
    #   2. the device API payload, when it exposes the key
    #   3. the IoT Agent admin API, for the device we just provisioned (needs
    #      kubectl access — the same the cluster checks already use)
    entity = session.device.main_entity
    tenant = (entity.tenant if entity else "") or config.tenant
    session.data_api_key = (
        config.data_api_key
        or api.discover_api_key(session.token, session.device)
        or kube.discover_device_apikey(
            session.device.serial,
            tenant,
            config.platform_namespace,
            servicepath=entity.scope if entity else "/",
        )
    )
    if not session.data_api_key:
        report.note(
            "DATA_API_KEY is not set and could not be discovered automatically — "
            "the device data path cannot be verified (it fails unless "
            "REQUIRE_DATA_PATH=false). Set DATA_API_KEY in environments/<name>/"
            "tests.env; tests/README.md ('Obtaining DATA_API_KEY and TENANT') "
            "explains how to read it from the IoT Agent."
        )


@pytest.mark.check(
    id="device-send-data",
    title="Device sends measurements (HTTP → fiware-manager → iot-agent)",
    section=SECTION,
)
@pytest.mark.api
def test_send_data():
    require("device-create")
    api_key = _require_api_key()

    _SENT_TEMPERATURES.clear()
    for attempt in range(DATA_SENDS):
        temperature = api.generate_random_temperature()
        result = api.send_data(
            session.device.serial, {"temperature": temperature}, api_key, get_cmd=0
        )
        if not result.success:
            fail(
                f"Sending measurement {attempt + 1}/{DATA_SENDS} failed "
                f"(HTTP {result.status_code})",
                f"Response: {result.body[:200]}",
                "401/403 usually means the API key is wrong for device type "
                f"'{config.device_type}' — set DATA_API_KEY in tests.env.",
                "Otherwise check the ingestion chain: "
                f"kubectl logs -n {config.platform_namespace} deploy/fiware-manager ; "
                f"kubectl logs -n {config.platform_namespace} deploy/iot-agent-json",
            )
        _SENT_TEMPERATURES.append(temperature)


@pytest.mark.check(
    id="device-entity-data",
    title="Entity reflects the sent data (orion-ld pipeline)",
    section=SECTION,
)
@pytest.mark.api
def test_entity_reflects_data():
    require("device-send-data")
    assert _SENT_TEMPERATURES, "no measurements were sent by the previous check"

    # Verify the entity reflects one of the values the device sent. We do NOT
    # require it to be the *last* one: several rapid, unsynchronised updates to
    # the same device settle on a non-deterministic winner in the async pipeline
    # (orion-ld keeps the reading with the latest server-side TimeInstant, and
    # processing order is not the send order). Matching any value the device
    # actually sent proves the ingestion → context-broker path works, which is
    # what this check is about.
    matched, last_value = api.wait_for_property_in(
        session.token,
        session.device.main_entity,
        "temperature",
        _SENT_TEMPERATURES,
    )
    if not matched:
        fail(
            f"Entity property 'temperature' is {last_value!r}, expected one of the "
            f"sent values {sorted(_SENT_TEMPERATURES)} (after retries)",
            "Data reached fiware-manager but is not visible on the entity. Check "
            "the context broker chain: "
            f"kubectl logs -n {config.platform_namespace} deploy/iot-agent-json ; "
            f"kubectl logs -n {config.platform_namespace} deploy/orion-ld",
            "Also verify MongoDB is healthy (orion-ld stores entities there).",
        )


@pytest.mark.check(
    id="device-command",
    title="Command roundtrip (send via API, device polls with getCmd=1)",
    section=SECTION,
)
@pytest.mark.api
def test_command_roundtrip():
    require("device-send-data")
    api_key = _require_api_key()

    if not session.device.main_entity_id:
        pytest.skip("device has no main entity id — cannot address commands")

    sent, error = api.send_command(session.token, session.device.main_entity_id, {"w_ota": True})
    if not sent:
        fail(
            f"Sending the command failed: {error}",
            f"Check web-back and orion-ld logs: kubectl logs -n "
            f"{config.platform_namespace} deploy/web-back",
        )

    # The device polls for pending commands by sending data with getCmd=1.
    result = api.send_data(
        session.device.serial,
        {"temperature": api.generate_random_temperature()},
        api_key,
        get_cmd=1,
    )
    if not result.success:
        fail(
            f"Polling for commands failed (HTTP {result.status_code})",
            f"Response: {result.body[:200]}",
        )

    try:
        response = json.loads(result.body)
    except ValueError:
        response = {}
    if "w_ota" not in response:
        fail(
            "Command 'w_ota' was not delivered to the device "
            f"(poll response: {result.body[:200] or '(empty)'})",
            "The command was accepted by the API but did not come back on the "
            "device poll. Check the command path: "
            f"kubectl logs -n {config.platform_namespace} deploy/orion-ld ; "
            f"kubectl logs -n {config.platform_namespace} deploy/iot-agent-json",
        )

    # The device must receive the value we sent (true), not just the command key.
    # Accept the platform's encodings of a boolean true (true / "true" / 1).
    delivered = response.get("w_ota")
    if str(delivered).strip().lower() not in ("true", "1"):
        fail(
            f"Command 'w_ota' was delivered with value {delivered!r}, expected the "
            "true we sent",
            "The command path delivered the command but mangled its value — check "
            f"kubectl logs -n {config.platform_namespace} deploy/orion-ld ; "
            f"kubectl logs -n {config.platform_namespace} deploy/iot-agent-json",
        )
