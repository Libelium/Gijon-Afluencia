from typing import Dict, List
import requests

from app.core.context_broker.context_broker_proxy.orion_v2_proxy.crud import utils
from aether_pylib.context_broker.create_entities_result import (
    CreateEntitiesResponse,
)
from aether_pylib.context_broker.update_entities_result import (
    EntityBatchOperationError,
    UpdateEntitiesResult,
)


def get_entity(orion_v2_service: str, urn: str, tenant: str, scope: str) -> Dict:
    """
    returns the entity with the given urn
    """

    session = requests.Session()
    response = session.get(
        f"{orion_v2_service}/v2/entities/{urn}",
        headers=utils.build_headers(tenant, scope),
    )

    if response.status_code != 200:
        return {}

    return response.json()


def get_entities(
    orion_v2_service: str, tenant: str, scope: str, types: List[str],
    limit: int | None = None, offset: int | None = None,
) -> Dict:
    """
    returns all the entities
    """

    params = {"type": ",".join(types)} if types else {}

    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset

    session = requests.Session()
    response = session.get(
        f"{orion_v2_service}/v2/entities",
        headers=utils.build_headers(tenant, scope),
        params=params if params else None,
    )

    if response.status_code != 200:
        return {}

    return response.json()


def create_entity(orion_v2_service: str, entity: Dict, tenant: str, scope: str) -> dict:
    """
    creates an entity. Returns a string if there was an error
    """

    session = requests.Session()
    response = session.post(
        f"{orion_v2_service}/v2/entities",
        headers=utils.build_headers(tenant, scope),
        json=entity,
    )

    if response.status_code != 201:
        return response.json()

    return None


def batch_entity_append(
    orion_v2_service: str, entities: List[Dict], tenant: str, scope: str
) -> UpdateEntitiesResult:
    """
    updates a batch of entities
    """

    session = requests.Session()
    response = session.post(
        f"{orion_v2_service}/v2/op/update",
        headers=utils.build_headers(tenant, scope),
        json={
            "actionType": "append",
            "entities": entities,
        },
    )

    return handle_batch_operation_response(response, entities)


def batch_entity_update(
    orion_v2_service: str, entities: List[Dict], tenant: str, scope: str
) -> UpdateEntitiesResult:
    """
    updates a batch of entities
    """

    session = requests.Session()
    response = session.post(
        f"{orion_v2_service}/v2/op/update",
        headers=utils.build_headers(tenant, scope),
        json={
            "actionType": "update",
            "entities": entities,
        },
    )

    return handle_batch_operation_response(response, entities)


def handle_batch_operation_response(
    response: Dict, entities: List[Dict]
) -> UpdateEntitiesResult:
    errors = []
    if response.status_code > 299:
        errors = handle_batch_error(response.json())

    # the updated ones are the ones without errors
    error_ids = [error.id for error in errors]
    print(error_ids)
    updated = [entity["id"] for entity in entities if entity["id"] not in error_ids]

    return UpdateEntitiesResult(
        updated=updated,
        errors=errors,
    )


def handle_batch_error(response: Dict) -> List[EntityBatchOperationError]:
    """
    handles the error response from a batch operation.
    Errors can be like this:
    do not exist: urn:ngsi-ld:Bell:00s3/Bell - [entity itself], urn:ngsi-ld:Bell:00s5/Bell [entity itself]
    This code is very specific to the Orion context broker, and i dont think
    there is any point on trying to discover the error message, since it is
    not documented, and it is not a good practice to rely on the error messages of these APIs
    """

    isKnown = response.get("error", None) == "PartialUpdate"

    if not isKnown:
        return [
            EntityBatchOperationError(
                id="",
                error=response,
            )
        ]

    description = response.get("description", None)
    if not description:
        return EntityBatchOperationError(
            id="",
            error="Unknown error",
        )

    if "do not exist" not in description:
        return [
            EntityBatchOperationError(
                id="",
                error=description,
            )
        ]

    failedEntities = description.replace("do not exist: ", "").split(", ")
    failedEntities = [
        entity.replace(" [entity itself]", "") for entity in failedEntities
    ]
    # now remove /{type} from the URN
    failedUrns = [entity.split("/")[0] for entity in failedEntities]
    # now split by spaces and get the URN
    failedUrns = [entity.split(" ")[0] for entity in failedUrns]

    return [
        EntityBatchOperationError(
            id=urn,
            error="Entity does not exist",
        )
        for urn in failedUrns
    ]
