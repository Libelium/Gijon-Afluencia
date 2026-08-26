from abc import ABC, abstractmethod
from typing import Any, List
from schemas.data_importation_request import DataImportationRequest
from schemas.entity_data_notification import EntityAttr, EntityDataNotification


class DataParser(ABC):
    """
    Abstract base class for parsing data from different file formats.
    Each parser is responsible for converting file content into a standardized
    format (list of EntityAttr objects).
    """

    @abstractmethod
    def parse(
        self,
        file_content: Any,
        request: DataImportationRequest,
    ) -> List[EntityDataNotification]:
        """ """
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """
        Get the file extension that this parser supports.

        Returns:
            File extension without the dot (e.g., 'csv', 'xlsx', 'json')
        """
        pass
