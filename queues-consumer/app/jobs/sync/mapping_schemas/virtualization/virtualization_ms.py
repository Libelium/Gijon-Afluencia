from models.mapping_schema_model import MappingSchema as MappingSchemaModel
from schemas.entity_data_notification import EntityAttr, EntityDataNotification
from jobs.sync.mapping_schemas.mapping_schema import MappingSchema
from config.logging import appLogging as logging
import models.crud.crud_entity as crud_entity
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
import models.crud.crud_entity as crud_entity

class VirtualizationMS(MappingSchema): 
    """
    VirtualizationMS represents a concrete implementation of a MappingSchema,
    used to transform attributes from an incoming entity notification according
    to a mapping definition and produce a new virtualized notification for another entity.
    """

    def __init__(
        self,
        mapping_schema: MappingSchemaModel,
        destination_entity_id: int,
        db: Session
     ):
        """
        Args:
            mapping_schema: The mapping schema model to be used for attribute transformation.
            destination_entity_id: The ID of the entity that will receive the transformed notification.
            db: SQLAlchemy session for DB operations.
        """

        self.mapping_schema = mapping_schema
        self.destination_entity_id = destination_entity_id
        self.db = db

    def apply(self, notification: EntityDataNotification) -> List[EntityDataNotification]:
        """
        Applies the mapping schema to transform the input notification into a virtualized one for the target entity.

        Args:
            notification: The original input notification.

        Returns:
            A list with the resulting virtualized EntityDataNotification.
        """

        mapeos_procesados, include_non_mapped  = self.__process_mapping_schema(self.mapping_schema.map)
        mapping_dict = {m["source"]: m["target"] for m in mapeos_procesados}

        all_attributes = notification.get_all_attributes()
        data = self.__process_attributes(all_attributes, mapping_dict, include_non_mapped)
        
        return self.__create_notification(data)

    
    def __process_mapping_schema(self, mapping_schema: Dict) -> Tuple[List[Dict[str, str]], bool]:
        """
        Processes a mapping schema by extracting the source-target pairs and
        the boolean value of the include_non_translated field.

        Returns:
            - A list of valid mappings: [{"source": ..., "target": ...}, ...]
            - The value of include_non_translated (bool), defaults to False if not present or not a boolean
        """

        processed = []
        include_non_translated = False

        try:
            mappings = mapping_schema.get("mapping", [])
            if not isinstance(mappings, list):
                mappings = []

            for i, m in enumerate(mappings):
                if not isinstance(m, dict):
                    continue

                source = m.get("source_attr")
                target = m.get("target_attr")

                if source is None or target is None:
                    continue

                processed.append({"source": source, "target": target})

            raw_value = mapping_schema.get("include_non_translated")
            if isinstance(raw_value, bool):
                include_non_translated = raw_value

        except Exception as e:
            logging.info(f"Error processing mapping_schema: {e}")
        
        return processed, include_non_translated
    

    def __process_attributes(
        self,
        all_attributes: List[EntityAttr],
        mapping_dict: Dict[str, str],
        include_non_mapped: bool
    ) -> List[EntityAttr]:

        """
        Applies the mapping to the attributes. If `include_non_mapped` is True, all attributes are included;
        if False, only those defined in the mapping are included. Attributes found in the mapping are always renamed.
        """

        result = []

        for attr in all_attributes:
            if include_non_mapped or attr.name in mapping_dict:
                if attr.name in mapping_dict:
                    renamed_attr = attr.model_copy(update={"name": mapping_dict[attr.name]})
                    result.append(renamed_attr)
                else:
                    result.append(attr)

        return result
    

    def __create_notification(self, data: List[EntityAttr]) ->  List[EntityDataNotification]:
        """
        Creates a new EntityDataNotification for the destination entity by fetching its metadata, 
        attaching related devices, and embedding the provided mapped attributes. 
        """
        destination_entity = crud_entity.get_entity_by_id(self.destination_entity_id,self.db)
        notification_data = EntityDataNotification(
                urn=destination_entity.urn,
                tenant=destination_entity.tenant,
                scope=destination_entity.scope,
                type=destination_entity.datamodel,
                db_id=destination_entity.id,
                devices=crud_entity.get_related_devices(destination_entity.id,self.db),
                data=data
            )


        return [notification_data]