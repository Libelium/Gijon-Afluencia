"""
Shared fixtures.

The zones of a deployment now live in storage (ote/zones/{tenant}/{scope}/zones.json,
see crowd_predictions/zones_config.py), not in the package. Tests seed the registry
directly from tests/fixtures/zones.json instead of going through storage: what they
exercise is the code that USES the zones, and every one of them needs the same
deterministic set. The loader itself has its own tests in test_zones_config.py.

Autouse so no test can accidentally reach for real storage - and reset afterwards,
because the registry caches per (tenant, scope) and tests move both around.
"""

import json
import os

import pytest

from crowd_predictions import zones_config

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "zones.json")


def zones_payload() -> dict:
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def _demo_target(monkeypatch):
    """A tenant/scope pair for every test that does not care about one: storage keys
    have no fallback any more (helpers/model_storage.tenant_scope). Tests that DO care
    override it - patch.dict(clear=True) included."""
    monkeypatch.setenv("FIWARE_TENANT", "demo_tenant")
    monkeypatch.setenv("FIWARE_SCOPE", "/")
    # Same reason: CALENDAR_TIMEZONE/HOLIDAYS_COUNTRY have no default either, so every
    # test gets one deployment's calendar. Those that assert on it set their own.
    monkeypatch.setenv("CALENDAR_TIMEZONE", "Europe/Madrid")
    monkeypatch.setenv("HOLIDAYS_COUNTRY", "ES")
    # SEC-019: the anomaly bundle is signed, and an unset key refuses to sign or
    # verify rather than falling back to a bare pickle, so every test that stores
    # a bundle needs one - exactly as a deployment does. Tests asserting on the
    # unconfigured case override it.
    monkeypatch.setenv("ANOMALY_STATE_HMAC_KEY", "test-anomaly-hmac-key")


@pytest.fixture(autouse=True)
def _seed_zones(monkeypatch):
    """Replaces only the STORAGE READ, not the registry: everything above it -
    parsing, the per-(tenant, scope) cache, the coordinate lookups - runs for real,
    so a bug there still fails the suite. test_zones_config.py covers the read
    itself, which is the one piece this stubs out."""
    monkeypatch.setattr(zones_config, "_load_payload", zones_payload)
    zones_config.reset_cache()
    yield
    zones_config.reset_cache()
