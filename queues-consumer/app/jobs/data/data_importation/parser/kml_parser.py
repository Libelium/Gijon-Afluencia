import json
import ast
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict

from config.logging import appLogging as logging
from dateutil.parser import parse
from schemas.data_importation_request import DataImportationRequest
from schemas.entity_data_notification import (
    EntityAttr,
    EntityAttrType,
    EntityDataNotification,
)
from jobs.data.data_importation.parser.parser import DataParser
from utils.ngsi.ngsi_ld_utils import is_valid_ngsi_ld_urn

class KmlParser(DataParser):
    def parse(self, file_content, request: DataImportationRequest) -> List[EntityDataNotification]:
        """
        Parse a KML file and convert its spatial and extended data into standardized
        EntityDataNotification objects.

        The parser extracts:
        - Timestamp: using ExtendedData "timestamp" or TimeStamp/when fallback
        - URN (entity_id): from ExtendedData (required)
        - Entity type: from ExtendedData "type"
        - Dynamic attributes found in ExtendedData/Data nodes
        - Location: converted to GeoJSON Point geometry when coordinates are present

        Multiple Placemarks belonging to the same entity (same URN) are grouped
        under a single EntityDataNotification with all their attributes consolidated.

        Args:
            file_content: Path to the KML file to be processed.
            request: Contains optional tenant and scope metadata.

        Returns:
            List of EntityDataNotification objects ready to be published.

        Raises:
            Exception: Any unexpected parsing or format error is logged and re-raised.
        """
        try:
            tree = ET.parse(file_content)
            root = tree.getroot()
            ns = {"kml": "http://www.opengis.net/kml/2.2"}

            notifications = {}
            entity_metadata = {}

            # Get all placemarks
            placemarks = root.findall(".//kml:Placemark", ns)

            for pm in placemarks:
                ts_value = self._get_extended_data(pm, "timestamp", ns)
                when_node = pm.find(".//kml:TimeStamp/kml:when", ns)

                if ts_value:
                    timestamp = parse(ts_value).timestamp()
                elif when_node is not None and when_node.text:
                    timestamp = parse(when_node.text.replace("Z", "")).timestamp()
                else:
                    logging.warning("Placemark without a valid timestamp. Skipping.")
                    continue
                urn = self._get_extended_data(pm, "entity_id", ns)
                if not urn:
                    logging.warning("Placemark without entity_id. Skipping.")
                    continue
                if not is_valid_ngsi_ld_urn(urn):
                    logging.warning(f"Skipping placemark, invalid NGSI-LD URN: {urn}")
                    continue

                # Extended properties
                properties = {}
                for data_node in pm.findall(".//kml:ExtendedData/kml:Data", ns):
                    key = data_node.get("name")
                    value_node = data_node.find("kml:value", ns)
                    if key and value_node is not None:
                        value = value_node.text
                        if key not in ("timestamp", "entity_id", "tenant", "scope", "type"):
                            properties[key] = self._parse_value(value)

                # Geometry extraction
                geometry = None
                coord_node = pm.find(".//kml:coordinates", ns)
                if coord_node is not None and coord_node.text:
                    parts = coord_node.text.strip().split(",")
                    if len(parts) >= 2:
                        lon, lat = float(parts[0]), float(parts[1])
                        geometry = {"type": "Point", "coordinates": [lon, lat]}

                if urn not in notifications:
                    notifications[urn] = []
                    entity_metadata[urn] = {
                        "tenant": self._get_extended_data(pm, "tenant", ns),
                        "scope": self._get_extended_data(pm, "scope", ns),
                        "type": self._get_extended_data(pm, "type", ns),
                    }

                # Convert each property into EntityAttr
                for key, value in properties.items():
                    notifications[urn].append(EntityAttr(
                        name=key,
                        value=value,
                        timestamp=timestamp,
                        type=EntityAttrType.PROPERTY,
                    ))

                if geometry:
                    notifications[urn].append(EntityAttr(
                        name="location",
                        value=geometry,
                        timestamp=timestamp,
                        type=EntityAttrType.PROPERTY,
                    ))

            result = []
            for urn, attrs in notifications.items():
                meta = entity_metadata[urn]
                tenant = request.tenant or meta.get("tenant")
                scope = request.scope or meta.get("scope")
                if bool(tenant) != bool(scope):
                    raise ValueError("Both 'tenant' and 'scope' must be provided together or neither")
                type_ = meta.get("type")
                if not type_:
                    raise ValueError("Missing required 'type' value in placemark ExtendedData")
                result.append(EntityDataNotification(
                    urn=urn,
                    tenant=tenant,
                    scope=scope,
                    type=type_,
                    notified_at=datetime.now().timestamp(),
                    data=attrs,
                ))

            return result

        except Exception as e:
            logging.error(f"Failed to parse KML: {e}", exc_info=True)
            raise

    def _get_extended_data(self, pm, name, ns):
        """Return value from ExtendedData if it exists."""
        node = pm.find(f".//kml:ExtendedData/kml:Data[@name='{name}']/kml:value", ns)
        return node.text if node is not None else None

    def get_file_extension(self):
        return "kml"

    def _parse_value(self, value):
        if value is None:
            return None

        # Try JSON-like structures
        if isinstance(value, str) and value.strip().startswith(("{", "[")):
            try:
                return json.loads(value)
            except:
                try:
                    return ast.literal_eval(value)
                except:
                    return value

        # Boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Number
        try:
            return float(value)
        except:
            return value
