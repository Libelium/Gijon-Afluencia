from collections import defaultdict
from typing import List, Tuple

import models.crud.crud_entity_properties as crud_entity_properties
from models.entity_model import Entity

from .snapshot_base import SnapshotPayloadBuilder

FLOW_PROPERTIES = ["origin", "destination", "count", "startDate"]


class FlowReadingsPayloadBuilder(SnapshotPayloadBuilder):
    """
    Flows of the last window (CrowdFlowEventETL) that leave from or arrive at the linked
    sensors, with each flow's share of everything that left its origin in that window:

    {"lecturas": [{"dpa": {"fechaLectura", "idOrigen", "descripcionOrigen", "idDestino",
                           "descripcionDestino", "total(%)"}}]}
    """

    def build_items(self) -> List[Tuple[str, dict]]:
        """
        Keyed by origin sensor: with the {id} variable, each origin gets one message with
        all its flows.
        """
        sensor_urns = self.__linked_sensor_urns()
        if not sensor_urns:
            return []

        flows = self.__flows_touching(sensor_urns)
        if not flows:
            return []

        # The ETL updates every flow entity with each run: older windows are flows that
        # did not happen in the last one.
        window = max(flow["startDate"] for flow in flows)
        flows = [flow for flow in flows if flow["startDate"] == window]

        # The share is computed over everything that left each origin, linked or not.
        origins = {flow["origin"] for flow in flows}
        totals = defaultdict(float)
        for flow in self.__flows_from(origins):
            if flow["startDate"] == window:
                totals[flow["origin"]] += flow["count"]

        names = self.names_by_urn(
            {flow["origin"] for flow in flows} | {flow["destination"] for flow in flows}
        )

        readings = []
        for flow in sorted(flows, key=lambda f: (f["origin"], f["destination"])):
            total = totals.get(flow["origin"]) or 0
            origin_id = self.urn_id(flow["origin"])
            readings.append(
                (
                    origin_id,
                    {
                        "dpa": {
                            "fechaLectura": self.iso_utc(window),
                            "idOrigen": origin_id,
                            "descripcionOrigen": names.get(flow["origin"], origin_id),
                            "idDestino": self.urn_id(flow["destination"]),
                            "descripcionDestino": names.get(
                                flow["destination"], self.urn_id(flow["destination"])
                            ),
                            "total(%)": round(flow["count"] * 100 / total, 2) if total else 0,
                        }
                    },
                )
            )

        return readings

    def __linked_sensor_urns(self) -> list:
        entity_ids = self.linked_entity_ids()
        if not entity_ids:
            return []

        rows = self.iris_db.query(Entity.urn).filter(Entity.id.in_(entity_ids)).all()
        return [row[0] for row in rows]

    def __flows_touching(self, urns) -> list:
        flow_ids = set(
            crud_entity_properties.get_entity_ids_with_property_value(
                "origin", list(urns), self.realtime_db
            )
        ) | set(
            crud_entity_properties.get_entity_ids_with_property_value(
                "destination", list(urns), self.realtime_db
            )
        )
        return self.__load_flows(flow_ids)

    def __flows_from(self, origins) -> list:
        flow_ids = crud_entity_properties.get_entity_ids_with_property_value(
            "origin", list(origins), self.realtime_db
        )
        return self.__load_flows(flow_ids)

    def __load_flows(self, flow_ids) -> list:
        flows = []
        for props in self.properties_by_entity(list(flow_ids), FLOW_PROPERTIES).values():
            if any(name not in props for name in FLOW_PROPERTIES):
                continue

            origin = props["origin"].value
            destination = props["destination"].value
            # origin == destination is the ETL's per-sensor aggregate, not a movement.
            if not origin or not destination or origin == destination:
                continue

            flows.append(
                {
                    "origin": origin,
                    "destination": destination,
                    "count": self.number(props["count"].value) or 0,
                    "startDate": self.iso_utc(props["startDate"].value),
                }
            )
        return flows
