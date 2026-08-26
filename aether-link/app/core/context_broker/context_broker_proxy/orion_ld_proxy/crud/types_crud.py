import requests

from app.core.context_broker.context_broker_proxy.orion_ld_proxy.crud import utils
from app.core.config.logging import appLogging as logging


def get_types(orion_ld_service: str, tenant: str, scope: str, context_url: str):
    """
    Return the list of data types from the Context Broker
    """

    session = requests.Session()
    response = session.get(
        f"{orion_ld_service}/ngsi-ld/v1/types",
        headers=utils.build_headers(tenant, scope, context_url),
    )

    if response.status_code != 200:
        logging.error(
            "Error retrieving data types from orion-ld: " + str(response.text)
        )
        return {}

    return response.json()
