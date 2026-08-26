from jobs.sync.mapping_schemas.virtualization.virtualization_ms import VirtualizationMS
from models.crud import crud_mapping_schema, crud_virtualizations
from jobs.sync.mapping_schemas.mapping_schema import MappingSchema
from models.mapping_schema_model import MappingSchema as MappingSchemaModel
from sqlalchemy.orm import Session
from schemas.entity_data_notification import EntityDataNotification
from typing import List
from config.logging import appLogging as logging


class MappingSchemaFactory:

    """
    Factory class responsible for retrieving all applicable mapping schema instances
    for a given notification, including device-level and entity-level virtualizations.

    It builds concrete implementations of MappingSchema (e.g., VirtualizationMS)
    based on the mapping schema IDs configured in the virtualizations.
    """

    def __init__(self):
        pass

    def get_mapping_schemas(
        self,
        db: Session,
        notification: EntityDataNotification,
    ) -> List[MappingSchema]:
        
        """
        Retrieves all virtualizations (device and entity level) associated with a given notification,
        and returns the corresponding MappingSchema instances.
        """

        result: List[MappingSchema] = []

        # Process virtualizations by device
        for dev_id in notification.devices or []:
            result.extend(self._create_schemas_from_virtualizations(db, "devices", dev_id))

        # Process virtualizations by entity
        result.extend(self._create_schemas_from_virtualizations(db, "entities", notification.db_id))

        return result

    def _create_schemas_from_virtualizations(
        self,
        db: Session,
        v_type: str,
        v_id: int
    ) -> List[MappingSchema]:
        """
        Helper function to retrieve virtualizations by type and ID,
        and build the corresponding MappingSchema instances.
        """
        schemas: List[MappingSchema] = []

        virtualizations = crud_virtualizations.get_virtualizations_by_type_id(db, v_type=v_type, v_id=v_id)
        logging.info(f"Virtualizations for {v_type} {v_id} :: {virtualizations}")

        for virt in virtualizations or []:
            schema = crud_mapping_schema.get_mapping_schema(db, virt.mapping_schema_id)
            if not schema:
                continue

            mapping_schema_instance = VirtualizationMS(
                mapping_schema=schema,
                destination_entity_id=virt.destination_entity_id,
                db=db,
            )
            schemas.append(mapping_schema_instance)

        return schemas
