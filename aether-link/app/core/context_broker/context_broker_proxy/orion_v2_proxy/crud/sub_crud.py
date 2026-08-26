from typing import Dict, List, Union
import requests
from aether_pylib.context_broker.ngsi_v2_subscription import NgsiV2Subscription
from app.core.config.logging import appLogging as logging
import app.core.context_broker.context_broker_proxy.orion_v2_proxy.crud.utils as utils


def get_subs(
    orion_v2_service: str, tenant: str, scope: str
) -> List[NgsiV2Subscription]:
    """
    Get all subscriptions for a given tenant and scope
    """

    session = requests.Session()
    response = session.get(
        f"{orion_v2_service}/v2/subscriptions",
        headers=utils.build_headers(tenant, scope),
    )

    if response.status_code != 200:
        logging.error(
            f"Error getting subscriptions: {response.status_code} {response.text}"
        )
        return []

    subscriptions = []
    for item in response.json():
        subscriptions.append(NgsiV2Subscription(**item))

    return subscriptions


def get_sub(
    orion_v2_service: str,
    tenant: str,
    scope: str,
    sub_id: str,
) -> Union[NgsiV2Subscription, None]:
    """
    Get a subscription by its id (tenant and scope are needed to build the headers)
    """
    session = requests.Session()
    response = session.get(
        f"{orion_v2_service}/v2/subscriptions/{sub_id}",
        headers=utils.build_headers(tenant, scope),
    )

    if response.status_code != 200:
        logging.error(
            f"Error getting subscription: {response.status_code} {response.text}"
        )
        return None

    return NgsiV2Subscription(**response.json())


def create_sub(
    orion_v2_service: str, tenant: str, scope: str, sub: NgsiV2Subscription
) -> str:
    """
    Create a subscription in the Context Broker
    and return the subscription id
    """

    session = requests.Session()
    body = utils.schema_to_json(sub)
    response = session.post(
        f"{orion_v2_service}/v2/subscriptions",
        headers=utils.build_headers(tenant, scope),
        json=body,
    )

    if response.status_code != 201:
        logging.error(
            f"Error creating subscription: {response.status_code} {response.text}"
        )
        return ""

    # return the last part of the location header /v2/subscriptions/{sub_id}
    location_header = response.headers.get("Location", None)
    if location_header == "":
        logging.error("Error getting location header")
        return None

    return location_header.split("/")[-1]


def patch_sub(
    orion_v2_service: str,
    tenant: str,
    scope: str,
    sub_id: str,
    sub: NgsiV2Subscription,
) -> bool:
    """
    Patch a subscription in the Context Broker
    """

    session = requests.Session()
    body = utils.schema_to_json(sub)
    response = session.patch(
        f"{orion_v2_service}/v2/subscriptions/{sub_id}",
        headers=utils.build_headers(tenant, scope),
        json=body,
    )

    if response.status_code != 204:
        logging.error(
            f"Error patching subscription: {response.status_code} {response.text}"
        )
        return False

    return True


def delete_sub(orion_v2_service: str, tenant: str, scope: str, sub_id: str) -> bool:
    """
    Delete a subscription in the Context Broker
    """

    session = requests.Session()
    response = session.delete(
        f"{orion_v2_service}/v2/subscriptions/{sub_id}",
        headers=utils.build_headers(tenant, scope),
    )

    if response.status_code != 204:
        logging.error(
            f"Error deleting subscription: {response.status_code} {response.text}"
        )
        return False

    return True
