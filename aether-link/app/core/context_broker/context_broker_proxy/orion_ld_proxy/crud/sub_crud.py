import requests

from app.core.context_broker.context_broker_proxy.orion_ld_proxy.crud import utils
from app.core.config.logging import appLogging as logging
from aether_pylib.context_broker.ngsi_ld_subscription import NgsiLdSubscription


def get_sub(
    orion_ld_service: str,
    tenant: str,
    scope: str,
    context_url: str,
    sub_id: str,
) -> NgsiLdSubscription:
    """
    Get a subscription by its id (tenant and scope are needed to build the headers)
    """
    session = requests.Session()
    response = session.get(
        f"{orion_ld_service}/ngsi-ld/v1/subscriptions/{sub_id}",
        headers=utils.build_headers(tenant, scope, context_url),
    )

    if response.status_code != 200:
        logging.error(
            f"Error getting subscription: {response.status_code} {response.text}"
        )
        return None

    return NgsiLdSubscription(
        **response.json(),
    )


def create_sub(
    orion_ld_service: str,
    tenant: str,
    scope: str,
    context_url: str,
    sub: NgsiLdSubscription,
) -> NgsiLdSubscription:
    """
    Create a subscription
    """
    session = requests.Session()
    response = session.post(
        f"{orion_ld_service}/ngsi-ld/v1/subscriptions",
        headers=utils.build_headers(tenant, scope, context_url),
        json=utils.schema_to_json(sub),
    )

    if response.status_code != 201:
        logging.error(
            f"Error creating subscription in orion-ld: {response.status_code} {response.text}"
        )
        return None

    return sub


def patch_sub(
    orion_ld_service: str,
    tenant: str,
    scope: str,
    context_url: str,
    sub_id: str,
    sub: NgsiLdSubscription,
) -> NgsiLdSubscription:
    """
    Patch a subscription
    """
    session = requests.Session()
    response = session.patch(
        f"{orion_ld_service}/ngsi-ld/v1/subscriptions/{sub_id}",
        headers=utils.build_headers(tenant, scope, context_url),
        json=utils.schema_to_json(sub),
    )

    if response.status_code != 204:
        logging.error(
            f"Error patching subscription in orion-ld: {response.status_code} {response.text}"
        )
        return None

    return sub


def delete_sub(
    orion_ld_service: str,
    tenant: str,
    scope: str,
    context_url: str,
    sub_id: str,
) -> bool:
    """
    Delete a subscription
    """
    session = requests.Session()
    response = session.delete(
        f"{orion_ld_service}/ngsi-ld/v1/subscriptions/{sub_id}",
        headers=utils.build_headers(tenant, scope, context_url),
    )

    if response.status_code != 204:
        logging.error(
            f"Error deleting subscription in orion-ld: {response.status_code} {response.text}"
        )
        return False

    return True
