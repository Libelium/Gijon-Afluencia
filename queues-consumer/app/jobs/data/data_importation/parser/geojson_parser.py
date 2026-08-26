import json
from datetime import datetime
from typing import List, Dict
from dateutil.parser import parse

from config.logging import appLogging as logging
from schemas.data_importation_request import DataImportationRequest
from schemas.entity_data_notification import (
    EntityAttr,
    EntityAttrType,
    EntityDataNotification,
)
from jobs.data.data_importation.parser.parser import DataParser
from utils.ngsi.ngsi_ld_utils import  is_valid_ngsi_ld_urn



class GeoJsonParser(DataParser):
    """
    Parse a GeoJSON FeatureCollection and convert its feature properties and
    geometries into standardized EntityDataNotification objects.

    Features are grouped by their "entity_id" property
    (must be a valid NGSI-LD URN format). The entity type and the urn are 
    extracted from the file.

    Extracted data:
    - Timestamp: taken from "timestamp" property (numeric or ISO8601)
    - Attributes: any feature property excluding "entity_id" and "timestamp"
    - Geometry: passed as-is if the feature contains a valid geometry

    Args:
        file_content: Path to the GeoJSON file to be loaded and processed.
        request: Metadata defaults such as tenant and scope.

    Returns:
        A list of EntityDataNotification objects, one per entity.
    """

    def parse(self, file_content, request: DataImportationRequest) -> List[EntityDataNotification]:
        try:
            with open(file_content, "r") as f:
                geojson = json.load(f)

            if geojson.get("type") != "FeatureCollection":
                raise ValueError("GeoJSON must be a FeatureCollection")

            features = geojson.get("features", [])
            if not features:
                raise ValueError("GeoJSON contains no features")

            grouped: Dict[str, List[dict]] = {}

            for feature in features:
                props = feature.get("properties", {})
                entity_id = props.get("entity_id")

                if not entity_id:
                    logging.warning("Skipping feature, missing entity_id")
                    continue
                if not is_valid_ngsi_ld_urn(entity_id):
                    logging.warning(f"Skipping feature, invalid NGSI-LD URN: {entity_id}")
                    continue

                grouped.setdefault(entity_id, []).append(feature)

            notifications = []

            for dev_urn, feats in grouped.items():
                attrs = self._build_attrs(feats)
                first_props = feats[0].get("properties", {})
                tenant = request.tenant or first_props.get("tenant")
                scope = request.scope or first_props.get("scope")
                if bool(tenant) != bool(scope):
                    raise ValueError("Both 'tenant' and 'scope' must be provided together or neither")
                type_ = first_props.get("type")
                if not type_:
                    raise ValueError("Missing required 'type' value in feature properties")
                notifications.append(self._create_notification(
                    dev_urn, attrs, tenant, scope, type_
                ))

            return notifications

        except Exception as e:
            logging.error(f"Failed to parse GeoJSON: {e}", exc_info=True)
            raise

    def _build_attrs(self, features: List[dict]) -> List[EntityAttr]:
        attr_list: List[EntityAttr] = []

        for feature in features:
            try:
                props = feature["properties"]
                geometry = feature.get("geometry")
                timestamp_raw = props.get("timestamp")

                try:
                    timestamp = float(timestamp_raw)
                except:
                    timestamp = parse(timestamp_raw).timestamp()

                for key, value in props.items():
                    if key in ["entity_id", "timestamp", "tenant", "scope", "type"]:
                        continue
                    attr_list.append(
                        EntityAttr(
                            name=key,
                            value=value,
                            timestamp=timestamp,
                            type=EntityAttrType.PROPERTY,
                        )
                    )

                if geometry:
                    attr_list.append(
                        EntityAttr(
                            name="location",
                            value=geometry,
                            timestamp=timestamp,
                            type=EntityAttrType.PROPERTY,
                        )
                    )

            except Exception as e:
                logging.warning(f"Malformed feature skipped: {e}")

        return attr_list

    def _create_notification(self, urn: str, attrs: List[EntityAttr], tenant: str, scope: str, type_: str):
        notified_at = datetime.now().timestamp()
        return EntityDataNotification(
            urn=urn,
            tenant=tenant,
            scope=scope,
            type=type_,
            notified_at=notified_at,
            data=attrs,
        )

    def get_file_extension(self):
        return "geojson"
