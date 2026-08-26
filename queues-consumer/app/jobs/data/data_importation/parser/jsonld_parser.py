import json
from datetime import datetime
from typing import List

from config.logging import appLogging as logging
from schemas.data_importation_request import DataImportationRequest
from schemas.entity_data_notification import EntityDataNotification
from jobs.data.data_importation.parser.parser import DataParser
from utils.ngsi.cb_notification_translator.ngsi_ld_notification_translator import (
    NgsiLdNormalizedNotificationTranslator,
)
from utils.ngsi.ngsi_ld_utils import is_valid_ngsi_ld_urn


class JsonLdParser(DataParser):
    """
    Parse a JSON-LD file containing NGSI-LD normalized entities and convert
    them into EntityDataNotification objects.

    Accepts either an array of entities or a single entity object.
    Reuses the existing NgsiLdNormalizedNotificationTranslator to handle
    the NGSI-LD normalized format natively.

    Args:
        file_content: Path to the JSON-LD file to be loaded and processed.
        request: Metadata defaults such as tenant and scope.

    Returns:
        A list of EntityDataNotification objects, one per entity.
    """

    def parse(self, file_content, request: DataImportationRequest) -> List[EntityDataNotification]:
        try:
            with open(file_content, "r") as f:
                data = json.load(f)

            # Normalize: accept single entity or array
            if isinstance(data, dict):
                entities = [data]
            elif isinstance(data, list):
                entities = data
            else:
                raise ValueError("JSON-LD file must contain an object or an array of objects")

            if not entities:
                raise ValueError("JSON-LD file contains no entities")

            translator = NgsiLdNormalizedNotificationTranslator()
            default_timestamp = datetime.now()
            if not request.tenant or not request.scope:
                raise ValueError("Both 'tenant' and 'scope' are required in the request for JSON-LD importation")
            tenant = request.tenant
            scope = request.scope

            notifications = []

            for entity in entities:
                if not isinstance(entity, dict):
                    logging.warning(f"Skipping non-object entry in JSON-LD array: {type(entity)}")
                    continue

                entity_id = entity.get("id")
                if not entity_id or not is_valid_ngsi_ld_urn(entity_id):
                    logging.warning(f"Skipping entity, invalid or missing URN: {entity_id}")
                    continue

                notification = translator.translate_entity(
                    entity, default_timestamp, tenant, scope
                )

                if notification is not None:
                    notifications.append(notification)
                else:
                    logging.warning(f"Skipping entity that could not be translated: {entity_id}")

            logging.info(f"Parsed {len(notifications)} entity/ies from JSON-LD file")

            return notifications

        except Exception as e:
            logging.error(f"Failed to parse JSON-LD file: {e}", exc_info=True)
            raise

    def get_file_extension(self):
        return "jsonld"
