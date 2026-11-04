from typing import List, Tuple

from models.entity_model import Entity

from .snapshot_base import SnapshotPayloadBuilder

OCCUPANCY_PROPERTY = "occupancy"
# Other datamodels also carry an occupancy attribute (a Smart Spot CrowdFlowObserved, for
# one), but only zones are points of interest.
ZONE_ENTITY_TYPE = "CrowdFlowZone"


class OccupancyReadingsPayloadBuilder(SnapshotPayloadBuilder):
    """
    Current occupancy of each linked point of interest (CrowdFlowZone entities):

    {"lecturas": [{"dpa": {"fechaLectura", "idPuntoInteres", "descripcionPuntoInteres", "total"}}]}
    """

    def build_items(self) -> List[Tuple[str, dict]]:
        entity_ids = self.linked_zone_ids()
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
                (
                    point_id,
                    {
                        "dpa": {
                            "fechaLectura": self.iso_utc(occupancy.timestamp),
                            "idPuntoInteres": point_id,
                            "descripcionPuntoInteres": name.value if name and name.value else point_id,
                            "total": self.number(occupancy.value),
                        }
                    },
                )
            )

        return readings

    def linked_zone_ids(self) -> List[int]:
        entity_ids = self.linked_entity_ids()
        if not entity_ids:
            return []

        rows = (
            self.iris_db.query(Entity.id)
            .filter(Entity.id.in_(entity_ids))
            .filter(Entity.datamodel == ZONE_ENTITY_TYPE)
            .all()
        )
        return [row[0] for row in rows]
