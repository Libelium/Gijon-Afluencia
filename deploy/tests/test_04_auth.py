"""
Stage 4 — authentication.

Logs into the platform API with the admin credentials from tests.env. This
exercises the full identity chain: web-back → Keycloak realm/clients → the
KEYCLOAK_* secrets wired by the generator and the post-install setup.

The token is shared with the device-flow stages through helpers.session.
"""

import pytest

from helpers import api, session
from helpers.report import require

SECTION = "Authentication"


@pytest.mark.check(
    id="auth-login",
    title="Admin login via /api/V1/login",
    section=SECTION,
)
@pytest.mark.api
def test_admin_login():
    require("endpoint-api")
    session.token = api.login()
