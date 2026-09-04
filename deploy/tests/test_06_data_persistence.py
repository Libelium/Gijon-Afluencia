"""
Stage 6 — data persistence (adapted from the platform integration-test suite).

Verifies the asynchronous persistence chain: measurements sent over HTTP must
land in timeseries storage and be retrievable through the public timeseries
API. This exercises carrot → RabbitMQ → cb/generic-consumer → TimescaleDB —
the part of the platform the lifecycle stage does not cover.

Uses its own short-lived device so it can run even when an earlier lifecycle
check failed for command-specific reasons.
"""

import time
from datetime import datetime, timedelta, timezone

import pytest

from helpers import api, session
from helpers.config import config
from helpers.report import fail, require

SECTION = "Data persistence (timeseries)"

DATA_POINTS = 5
PERSISTENCE_WAIT_SECONDS = 5
SEND_WINDOW_OFFSET_SECONDS = 60
# Reuse the shared propagation budget: persistence is the slowest async chain
# (carrot → RabbitMQ → consumers → TimescaleDB), so it must not be tighter than
# the entity-update poll.
QUERY_RETRIES = config.propagation_attempts
QUERY_RETRY_WAIT_SECONDS = config.propagation_interval


@pytest.mark.check(
    id="persistence-timeseries",
    title=f"{DATA_POINTS} measurements persisted and retrievable via timeseries API",
    section=SECTION,
)
@pytest.mark.api
def test_data_persists_to_timeseries():
    require("auth-login", "device-send-data")
    token = session.token

    device = session.device
    if device is None:
        pytest.skip("blocked: no device under test (TEST_DEVICE_SERIAL is not set)")

    sent = _send_data_points(device)

    time.sleep(PERSISTENCE_WAIT_SECONDS)

    tenant = config.tenant or device.main_entity.tenant
    start = sent[0]["timestamp"] - timedelta(seconds=2)
    end = sent[-1]["timestamp"] + timedelta(seconds=2)
    values = _query_with_retry(
        token, device, tenant, start, end, expected=len(sent)
    )

    if len(values) < len(sent):
        fail(
            f"Only {len(values)}/{len(sent)} data points found in timeseries "
            f"storage (tenant '{tenant}')",
            "Data reaches the entity but is not persisted. This is the "
            "asynchronous chain — check each hop:",
            f"kubectl logs -n {config.platform_namespace} deploy/carrot — pushes "
            "entity changes to RabbitMQ",
            f"kubectl logs -n {config.platform_namespace} deploy/cb-consumer ; "
            f"kubectl logs -n {config.platform_namespace} deploy/generic-consumer "
            "— consume the queues and write to TimescaleDB",
            "kubectl get pods -n rabbitmq — the broker must be running, and "
            "the pid-gijon vhost/user must exist (created by charts/rabbitmq).",
        )

    sent_temperatures = sorted(point["temperature"] for point in sent)
    stored_temperatures = sorted(
        value.get("value") for value in values if value.get("value") is not None
    )
    for temperature in sent_temperatures:
        found = any(
            isinstance(stored, (int, float))
            and abs(float(stored) - temperature) < 0.01
            for stored in stored_temperatures
        )
        if not found:
            fail(
                f"Sent temperature {temperature} not found in timeseries "
                f"(stored: {stored_temperatures})",
                "Values were persisted but do not match what was sent — check "
                "cb-consumer/generic-consumer logs for transformation errors.",
            )


def _send_data_points(device):
    sent = []
    # Series rows are keyed by (time, entity, attr), and the lifecycle stage
    # sends without TimeInstant, so starting at "now" would let one of these
    # points share a second with those sends and overwrite it.
    base_time = datetime.now(timezone.utc) - timedelta(seconds=SEND_WINDOW_OFFSET_SECONDS)
    for index in range(DATA_POINTS):
        temperature = api.generate_random_temperature()
        timestamp = base_time + timedelta(seconds=index)
        result = api.send_data(
            device.serial,
            {"temperature": temperature, "TimeInstant": timestamp.isoformat()},
            session.data_api_key,
            get_cmd=0,
        )
        if not result.success:
            fail(
                f"Sending data point {index + 1}/{DATA_POINTS} failed "
                f"(HTTP {result.status_code})",
                f"Response: {result.body[:200]}",
            )
        sent.append({"temperature": temperature, "timestamp": timestamp})
    return sent


def _query_with_retry(token, device, tenant, start, end, expected):
    values = []
    response = None
    for attempt in range(QUERY_RETRIES):
        if attempt:
            time.sleep(QUERY_RETRY_WAIT_SECONDS)
        response = api.query_timeseries(
            token,
            device.main_entity.urn,
            "temperature",
            tenant,
            start,
            end,
            limit=expected + 10,
        )
        if response is None:
            continue
        values = api.extract_timeseries_values(
            response, device.main_entity.urn, "temperature"
        )
        if len(values) >= expected:
            return values

    if not values and response is None:
        fail(
            "Timeseries API query failed (no successful response after "
            f"{QUERY_RETRIES} attempts)",
            f"Endpoint: {config.api_url}/api/V1/timeseries",
            f"Check web-back and aether-link: kubectl logs -n "
            f"{config.platform_namespace} deploy/web-back ; kubectl logs -n "
            f"{config.platform_namespace} deploy/aether-link",
        )
    return values
