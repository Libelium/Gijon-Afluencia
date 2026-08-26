from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Load the env file
load_dotenv()

@dataclass
class KeycloakConfig:
    """
    Class with the keycloak configuration of the queue consumer process
    """
    URL: str = os.getenv("KEYCLOAK_URL", "kc_url")
    USER: str = os.getenv("KEYCLOAK_USER", "kc_user")
    PASSWORD: str = os.getenv("KEYCLOAK_PASSWORD", "kc_password")
    CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID", "kc_client_id")
    
    