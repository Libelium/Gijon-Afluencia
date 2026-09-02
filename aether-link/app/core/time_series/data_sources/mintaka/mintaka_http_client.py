from typing import Optional, Tuple

import requests

from app.core.config.logging import appLogging as logging


class MintakaHttpClient:
    """HTTP transport for the Mintaka data source: the health probe and executing a
    prepared temporal query over a shared session.

    Extracted from MintakaDataSource so the status/None handling and error logging stop
    being copy-pasted across the entity and paginated read paths, and the data source is
    left with the pagination/merge logic only.
    """

    def __init__(self, service_url: str):
        self.service_url = service_url

    def health_check(self) -> bool:
        """
        Check if the data source is reachable (mintaka info endpoint)
        """
        response = requests.get(self.service_url + "/info")
        logging.info(
            "Mintaka health check: " + str(response.status_code) + " " + response.text
        )
        if response.status_code == 200:
            return True
        raise Exception(
            f"Mintaka health check failed: {response.status_code}\n" + response.text
        )

    def send(
        self, session: requests.Session, query: requests.PreparedRequest
    ) -> Tuple[Optional[object], Optional[str]]:
        """
        Execute a prepared query over the given session and return
        ``(response_json, next_page)``.

        On a status other than 200/206, or a null JSON body, ``response_json`` is None
        (the error is logged here, exactly as it was inline before) and the caller is
        expected to return its own empty result. ``next_page`` carries the Next-Page
        header for the paginated read path.
        """
        response = session.send(query)

        if response.status_code not in [200, 206]:
            logging.error(
                "Error retrieving data from mintaka: "
                + str(response.status_code)
                + " "
                + response.text
            )
            return None, None

        response_json = response.json()

        if response_json is None:
            logging.error("None response received from Mintaka")

        return response_json, response.headers.get("Next-Page")
