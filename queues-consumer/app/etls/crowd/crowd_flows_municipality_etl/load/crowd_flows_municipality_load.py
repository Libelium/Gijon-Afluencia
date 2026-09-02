import pandas as pd
import models.crud.crud_entity as crud_entity
from sqlalchemy.orm import Session
from schemas.crowd_flows_municipality_request_schema import (
    CrowdFlowsMunicipalityRequest,
)
import db.realtime as realtime_db
from db import deps
from datetime import timedelta
from etls.crowd.base_crowd_entity_load import BaseCrowdEntityLoad

# Retained as the module-level monkeypatch surface the load tests rely on: the shared
# publishing pipeline lives in BaseCrowdEntityLoad but references these same module
# objects, so patching them here (e.g. crowd_flows_municipality_load.iota_helper) still
# intercepts the calls the base class makes.
import helpers.aether_link.aether_link_helper as aether_link_helper  # noqa: F401
import models.crud.crud_tenant_scope as crud_tenant_scope  # noqa: F401
import models.crud.crud_preferences as crud_preferences  # noqa: F401
from helpers.iota import iota_helper  # noqa: F401


class CrowdFlowsMunicipalityLoad(BaseCrowdEntityLoad):

    def __init__(
        self,
        request: CrowdFlowsMunicipalityRequest,
        transform_output: dict,
        main_db: Session = next(deps.get_db()),
        realtime_db: Session = next(realtime_db.get_db_realtime()),
    ):
        # DB Sessions
        self.main_db = main_db
        self.realtime_db = realtime_db

        # Transform Output
        self.result = transform_output["result"]

        # Request
        self.entities = request.entities
        self.start_date = request.start_date
        self.end_date = request.end_date
        self.mode = request.mode
        self.user_id = request.user_id

        # Constants
        self.use_classification = True


    def _generate_entity_payload(self, data: dict) -> dict:
        payload = []

        flow_entity_urns = []
        flow_ids = []

        sensors_by_urn = {e.urn: e for e in self.entities}

        for flow in data:
            flow_origin_id = self._get_entity_id_from_urn(flow["origin"])
            flow_destination_id = self._get_entity_id_from_urn(flow["destination"])

            if flow_origin_id == flow_destination_id:
                flow_id = f"{flow_origin_id}"
            else:
                flow_id = f"{flow_origin_id}:{flow_destination_id}"

            flow_ids.append(flow_id)
            flow_entity_urns.append(f"urn:ngsi-ld:CrowdFlowEventETL:{flow_id}")

        existing_flows = crud_entity.get_many_by_urn(self.main_db, flow_entity_urns)
        existing_flow_urns = {e.urn for e in existing_flows}

        for i, flow in enumerate(data):
            flow_id = flow_ids[i]
            flow_entity_urn = flow_entity_urns[i]

            new_flow = {
                "entityId": flow_id,
                "origin": flow["origin"],
                "destination": flow["destination"],
                "averageTransitDuration": (
                    flow["averageTransitDuration"].total_seconds()
                    if isinstance(flow["averageTransitDuration"], timedelta)
                    else None
                ),
                "minimumTransitDuration": (
                    flow["minimumTransitDuration"].total_seconds()
                    if isinstance(flow["minimumTransitDuration"], timedelta)
                    else None
                ),
                "maximumTransitDuration": (
                    flow["maximumTransitDuration"].total_seconds()
                    if isinstance(flow["maximumTransitDuration"], timedelta)
                    else None
                ),
                "count": flow["count"] if flow["count"] else 0,
                    "touristAverageTransitDuration": (
                        flow["touristAverageTransitDuration"].total_seconds()
                        if isinstance(
                            flow["touristAverageTransitDuration"], timedelta
                        )
                        else None
                    ),
                    "touristMinimumTransitDuration": (
                        flow["touristMinimumTransitDuration"].total_seconds()
                        if isinstance(
                            flow["touristMinimumTransitDuration"], timedelta
                        )
                        else None
                    ),
                    "touristMaximumTransitDuration": (
                        flow["touristMaximumTransitDuration"].total_seconds()
                        if isinstance(
                            flow["touristMaximumTransitDuration"], timedelta
                        )
                        else None
                    ),
                    "touristCount": (
                        flow["touristCount"] if flow["touristCount"] else 0
                    ),
                    "residentAverageTransitDuration": (
                        flow["residentAverageTransitDuration"].total_seconds()
                        if isinstance(
                            flow["residentAverageTransitDuration"], timedelta
                        )
                        else None
                    ),
                    "residentMinimumTransitDuration": (
                        flow["residentMinimumTransitDuration"].total_seconds()
                        if isinstance(
                            flow["residentMinimumTransitDuration"], timedelta
                        )
                        else None
                    ),
                    "residentMaximumTransitDuration": (
                        flow["residentMaximumTransitDuration"].total_seconds()
                        if isinstance(
                            flow["residentMaximumTransitDuration"], timedelta
                        )
                        else None
                    ),
                    "residentCount": (
                        flow["residentCount"] if flow["residentCount"] else 0
                    ),
                    "shortTermVisitorAverageTransitDuration": (
                        flow[
                            "shortTermVisitorAverageTransitDuration"
                        ].total_seconds()
                        if isinstance(
                            flow["shortTermVisitorAverageTransitDuration"],
                            timedelta,
                        )
                        else None
                    ),
                    "shortTermVisitorMinimumTransitDuration": (
                        flow[
                            "shortTermVisitorMinimumTransitDuration"
                        ].total_seconds()
                        if isinstance(
                            flow["shortTermVisitorMinimumTransitDuration"],
                            timedelta,
                        )
                        else None
                    ),
                    "shortTermVisitorMaximumTransitDuration": (
                        flow[
                            "shortTermVisitorMaximumTransitDuration"
                        ].total_seconds()
                        if isinstance(
                            flow["shortTermVisitorMaximumTransitDuration"],
                            timedelta,
                        )
                        else None
                    ),
                    "shortTermVisitorCount": (
                        flow["shortTermVisitorCount"]
                        if flow["shortTermVisitorCount"]
                        else 0
                    ),
                    "TimeInstant": self.start_date.isoformat(),
                    "startDate": self.start_date.isoformat(),
                    "endDate": self.end_date.isoformat(),
                    
                }
                

            if flow_entity_urn not in existing_flow_urns:
                origin_sensor = sensors_by_urn.get(flow["origin"])
                dest_sensor = sensors_by_urn.get(flow["destination"])

                origin_name = (
                    origin_sensor.name
                    if origin_sensor and origin_sensor.name
                    else self._get_entity_id_from_urn(flow["origin"])
                )
                dest_name = (
                    dest_sensor.name
                    if dest_sensor and dest_sensor.name
                    else self._get_entity_id_from_urn(flow["destination"])
                )

                if flow["origin"] == flow["destination"]:
                    name = origin_name
                else:
                    name = f"From {origin_name} to {dest_name}"
                new_flow["name"] = name

            payload.append(new_flow)

        return payload

    def _process_to_fiware(self, df: pd.DataFrame) -> dict:
        """
        Function to process data to Fiware and returns a json
        """
        # Rename columns to match required JSON format
        mapping = {
            "origin_entityid": "origin",
            "entityid": "destination",
            "averagetransitduration": "averageTransitDuration",
            "minimumtransitduration": "minimumTransitDuration",
            "maximumtransitduration": "maximumTransitDuration",
            "count": "count",
            "touristaveragetransitduration": "touristAverageTransitDuration",
            "touristminimumtransitduration": "touristMinimumTransitDuration",
            "touristmaximumtransitduration": "touristMaximumTransitDuration",
            "touristcount": "touristCount",
            "residentaveragetransitduration": "residentAverageTransitDuration",
            "residentminimumtransitduration": "residentMinimumTransitDuration",
            "residentmaximumtransitduration": "residentMaximumTransitDuration",
            "residentcount": "residentCount",
            "shorttermvisitoraveragetransitduration": "shortTermVisitorAverageTransitDuration",
            "shorttermvisitorminimumtransitduration": "shortTermVisitorMinimumTransitDuration",
            "shorttermvisitormaximumtransitduration": "shortTermVisitorMaximumTransitDuration",
            "shorttermvisitorcount": "shortTermVisitorCount",
        }

        # Rename the columns in the dataframe
        df = df.rename(columns=mapping)

        # Convert dataframe to list of dictionaries
        js = df.to_dict(orient="records")

        # Generate the entity payload
        self.iota_payload = self._generate_entity_payload(js)

        return self.iota_payload
