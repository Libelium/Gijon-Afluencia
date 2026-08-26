from typing import Dict, List
import requests

from app.core.context_broker.context_broker_proxy.orion_ld_proxy.crud import utils
from app.core.config.logging import appLogging as logging
from aether_pylib.context_broker.update_entities_result import (
    EntityBatchOperationError,
    UpdateEntitiesResult,
)
from aether_pylib.context_broker.delete_entities_result import (
    EntityBatchOperationError,
    DeleteEntitiesResult,
)


def create_entities(
    orion_ld_service: str,
    tenant: str,
    scope: str,
    context_url: str,
    entities: Dict,
):
    """
    Create a list of entities
    """
    session = requests.Session()

    response = session.post(
        f"{orion_ld_service}/ngsi-ld/v1/entityOperations/create",
        headers=utils.build_headers(tenant, scope, context_url),
        json=entities,
    )

    return response


def get_entities(
    orion_ld_service: str, tenant: str, scope: str, context_url: str, types: List[str],
    limit: int | None = None, offset: int | None = None,
):
    """
    Get entities by type, with optional limit/offset pagination.
    """

    params = {"type": ",".join(types), "options": "sysAttrs"}

    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset

    response = requests.get(
        f"{orion_ld_service}/ngsi-ld/v1/entities",
        headers=utils.build_headers(tenant, scope, context_url),
        params=params,
    )

    if response.status_code != 200:
        logging.error("Error retrieving entities from orion-ld: " + str(response.text))

        # raise exception with the http status code
        response.raise_for_status()
        raise requests.exceptions.HTTPError(response.text, response=response)

    return response.json()


def get_entity(
    orion_ld_service: str, tenant: str, scope: str, context_url: str, entity_id: str
):
    """
    Get an entity by its id
    """

    response = requests.get(
        f"{orion_ld_service}/ngsi-ld/v1/entities/{entity_id}",
        headers=utils.build_headers(tenant, scope, context_url),
        params={"options": "sysAttrs"},
    )

    if response.status_code == 404:
        return None

    if response.status_code != 200:
        logging.error("Error retrieving entity from orion-ld: " + str(response.text))
        response.raise_for_status()
        raise requests.exceptions.HTTPError(response.text, response=response)

    return response.json()


def update_entities(
    orion_ld_service: str,
    tenant: str,
    scope: str,
    context_url: str,
    entities: Dict,
    params: Dict,
):
    """
    Update a list of entities
    """
    session = requests.Session()

    response = session.post(
        f"{orion_ld_service}/ngsi-ld/v1/entityOperations/update",
        headers=utils.build_headers(tenant, scope, context_url),
        json=entities,
        params=params,
    )

    return response


def send_commands(
    orion_ld_service: str,
    tenant: str,
    scope: str,
    context_url: str,
    commands_by_entity: Dict,
) -> UpdateEntitiesResult:
    """
    Send a list of commands
    """
    session = requests.Session()
    updated = []
    errors = []
    for urn, commands in commands_by_entity.items():
        url = f"{orion_ld_service}/ngsi-ld/v1/entities/{urn}/attrs"
        errors_in_entity = {}
        for command in commands:
            request_url = f"{url}/{command['name']}"
            logging.info(f"Sending command to {request_url}")

            prepared_request = session.prepare_request(
                requests.Request(
                    "PATCH",
                    request_url,
                    headers=utils.build_headers(tenant, scope, context_url),
                    json={
                        "value": utils.to_ngsi_null_if_none(command.get("value", None)),
                    },
                )
            )

            response = session.send(prepared_request)

            if response.status_code != 204:
                errors_in_entity[command["name"]] = {
                    "status": response.status_code,
                    "message": response.text,
                }

                logging.error(
                    f"Error sending command to {request_url}: {response.status_code} - {response.text}"
                )

        if len(errors_in_entity) > 0:
            errors.append(EntityBatchOperationError(id=urn, error=errors_in_entity))
        else:
            updated.append(urn)

    session.close()

    return UpdateEntitiesResult(updated=updated, errors=errors)


def delete_entities(
    orion_ld_service: str,
    tenant: str,
    scope: str,
    context_url: str,
    entities: List[str],
):
    """
    Delete a list of entities
    """
    session = requests.Session()
    deleted_ids = []
    errors = []
    for entity_urn in entities:
        try:
            response = session.delete(
                f"{orion_ld_service}/ngsi-ld/v1/entities/{entity_urn}",
                headers=utils.build_headers(tenant, scope, context_url),
            )

            if response.status_code == 204:
                deleted_ids.append(entity_urn)
            elif response.status_code == 404:
                errors.append(
                    EntityBatchOperationError(
                        id=entity_urn,
                        error={"message": "Entity not found", "status": 404},
                    )
                )
                logging.warning(f"Entity {entity_urn} not found for delete.")
            else:
                # Handle other error codes
                error_detail = response.text or f"Status Code: {response.status_code}"
                errors.append(
                    EntityBatchOperationError(
                        id=entity_urn,
                        error={
                            "message": f"Error deleting entity: {error_detail}",
                            "status": response.status_code,
                        },
                    )
                )
                logging.error(
                    f"Error deleting entity {entity_urn}: {response.status_code} - {response.text}"
                )

        except requests.exceptions.RequestException as e:
            errors.append(
                EntityBatchOperationError(
                    id=entity_urn,
                    error={
                        "message": f"Network or connection error: {str(e)}",
                        "status": 500,
                    },
                )
            )
            logging.error(f"Request error deleting entity {entity_urn}: {e}")

    session.close()
    return DeleteEntitiesResult(entities=deleted_ids, errors=errors)


def delete_entity_attribute(
    orion_ld_service: str,
    tenant: str,
    scope: str,
    context_url: str,
    entity_id: str,
    attr_name: str,
) -> requests.Response:
    """
    Delete an attribute from an entity
    """
    response = requests.delete(
        f"{orion_ld_service}/ngsi-ld/v1/entities/{entity_id}/attrs/{attr_name}",
        headers=utils.build_headers(tenant, scope, context_url),
    )
    return response

