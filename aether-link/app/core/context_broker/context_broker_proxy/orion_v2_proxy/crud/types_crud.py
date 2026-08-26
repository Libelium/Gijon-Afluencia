from typing import Dict, List, Union
import requests
from app.core.config.logging import appLogging as logging
import app.core.context_broker.context_broker_proxy.orion_v2_proxy.crud.utils as utils


def get_types(orion_v2_service: str, tenant: str, scope: str):
    """
    Get all data types for a given tenant and scope
    """

    session = requests.Session()
    response = session.get(
        f"{orion_v2_service}/v2/types",
        headers=utils.build_headers(tenant, scope),
    )

    if response.status_code != 200:
        logging.error(
            f"Error listing data types: {response.status_code} {response.text}"
        )
        return []

    return response.json()
