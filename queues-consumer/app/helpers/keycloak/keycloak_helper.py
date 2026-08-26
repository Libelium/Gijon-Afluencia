from typing import List, Optional
import requests
from config.config import settings
from config.logging import appLogging as logging
from models.crud.crud_user import get_user_by_id
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.session import SessionLocal
from urllib.parse import urlencode


class KeycloakTokenResponse(BaseModel):
    access_token: str
    expires_in: int
    refresh_expires_in: int
    refresh_token: str
    token_type: str


def get_keycloak_token() -> KeycloakTokenResponse | None:
    """
    Returns a keycloak token
    """

    try:
        data = {
            "client_id": settings.KEYCLOAK.CLIENT_ID,
            "username": settings.KEYCLOAK.USER,
            "password": settings.KEYCLOAK.PASSWORD,
            "grant_type": "password",
        }

        response = requests.post(
            f"{settings.KEYCLOAK.URL}/realms/pid-gijon/protocol/openid-connect/token",
            data=urlencode(data),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=settings.DEFAULT_EXTERNAL_REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        return KeycloakTokenResponse(**response.json())

    except Exception as e:
        logging.error(e)
        return None


def get_user_token(
    id: int, db: Optional[Session] = None
) -> KeycloakTokenResponse | None:
    """
    Returns a user token.

    The DB session must be obtained per call (and closed afterwards) — capturing
    it as a default argument evaluates it once at module load and keeps the
    underlying connection checked out forever, which deadlocks the pool
    (pool_size=1, max_overflow=0) when other code tries to acquire a connection.
    """

    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        token = get_keycloak_token()

        user = get_user_by_id(id, db)

        if not token or not user:
            return None

        data = {
            "client_id": settings.KEYCLOAK.CLIENT_ID,
            "subject_token": token.access_token,
            "requested_subject": user.keycloak_client_id,
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        }

        response = requests.post(
            f"{settings.KEYCLOAK.URL}/realms/pid-gijon/protocol/openid-connect/token",
            data=urlencode(data),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=settings.DEFAULT_EXTERNAL_REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        return KeycloakTokenResponse(**response.json())

    except Exception as e:
        logging.error(e)
        return None
    finally:
        if own_session:
            db.close()
