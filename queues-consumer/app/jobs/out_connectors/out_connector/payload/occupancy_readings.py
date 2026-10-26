from typing import Optional

from .snapshot_base import SnapshotPayloadBuilder

OCCUPANCY_PROPERTY = "occupancy"


class OccupancyReadingsPayloadBuilder(SnapshotPayloadBuilder):
    """
    Current occupancy of each linked point of interest (CrowdFlowZone entities):

    {"lecturas": [{"dpa": {"fechaLectura", "idPuntoInteres", "descripcionPuntoInteres", "total"}}]}
    """

    def build_payload(self) -> Optional[dict]:
        entity_ids = self.linked_entity_ids()
        properties = self.properties_by_entity(entity_ids, [OCCUPANCY_PROPERTY, "name"])

        readings = []
        for entity_id in sorted(properties):
            props = properties[entity_id]
            occupancy = props.get(OCCUPANCY_PROPERTY)
            if occupancy is None:
                continue

            name = props.get("name")
            point_id = self.urn_id(occupancy.urn)
            readings.append(
                {
                    "dpa": {
                        "fechaLectura": self.iso_utc(occupancy.timestamp),
                        "idPuntoInteres": point_id,
                        "descripcionPuntoInteres": name.value if name and name.value else point_id,
                        "total": self.number(occupancy.value),
                    }
                }
            )

        return {"lecturas": readings} if readings else None
