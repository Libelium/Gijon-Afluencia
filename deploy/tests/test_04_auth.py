"""
Stage 4 — authentication.

Mints an admin token at Keycloak with the credentials from tests.env and checks
that the management API accepts it. This exercises the full identity chain:
Keycloak realm/clients → the KEYCLOAK_* secrets wired by the generator and the
post-install setup → token validation in web-back.

The management API has no login endpoint: sign-in is authorization code + PKCE
against Keycloak, so the suite goes to the identity provider directly.

The token is shared with the device-flow stages through helpers.session.
"""

import pytest

from helpers import api, session
from helpers.report import require

SECTION = "Authentication"


@pytest.mark.check(
    id="auth-login",
    title="Admin token from Keycloak accepted by the API",
    section=SECTION,
)
@pytest.mark.api
def test_admin_login():
    require("endpoint-api")
    session.token = api.login()
    api.whoami(session.token)
