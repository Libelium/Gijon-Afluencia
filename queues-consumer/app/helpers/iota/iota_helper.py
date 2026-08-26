"""
A simple helper to publish information into the FIWARE IOT Agent
"""

import requests
from config.config import settings
from config.logging import appLogging as logging
import helpers.aether_link.aether_link_helper as aether_link_helper


def publish_data(id: str, apikey: str, body: dict, resource: str = "/iot/json"):
    """
    Publishes data into the IOT Agent. The resource is the endpoint to publish the data
    (e.g. /iot/json). The body is the data to be published.
    It raises an exception if the request fails.
    """

    response = requests.post(
        f"{settings.IOTA_URL}{resource}",
        params={
            "i": id,
            "k": apikey,
        },
        json=body,
        headers={"Content-Type": "application/json"},
        timeout=settings.DEFAULT_EXTERNAL_REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    if response.status_code not in [200, 201]:
        raise Exception(
            f"Error sending data to iot agent: {response.text} with status code {response.status_code}"
        )
