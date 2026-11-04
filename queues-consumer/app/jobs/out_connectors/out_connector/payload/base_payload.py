from abc import ABC, abstractmethod
from typing import Dict, List

from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.crud.crud_custom_datamodels import get_custom_datamodel_by_command_bulk
from schemas.entity_data_notification import EntityDataNotification


class BasePayloadBuilder(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def build_payload(self, entity_data: EntityDataNotification) -> BaseModel:
        pass

    @staticmethod
    def get_attr_names_map(
        attr_names: List[str],
        use_readable_names: bool,
        iris_db: Session,
    ) -> Dict[str, str]:
        """
        Build a mapping from attribute command codes to readable names using a single bulk DB query.
        Returns a dict mapping original attr_name -> readable name (falls back to original if not found).
        """
        if not use_readable_names:
            return {name: name for name in attr_names}

        custom_datamodels = get_custom_datamodel_by_command_bulk(attr_names, iris_db)
        name_map = {cd.command: cd.name for cd in custom_datamodels if cd.name}
        return {name: name_map.get(name, name) for name in attr_names}
