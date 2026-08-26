import pandas as pd
from typing import Tuple
from config.logging import appLogging as logging
import helpers.aether_link.aether_link_helper as aether_link_helper
from models.entity_model import Entity
from models.preferences_model import PreferenceType
import models.crud.crud_tenant_scope as crud_tenant_scope
import models.crud.crud_preferences as crud_preferences
import models.crud.crud_entity as crud_entity
from sqlalchemy.orm import Session
from schemas.crowd_flows_municipality_request_schema import (
    CrowdFlowsMunicipalityRequest,
)
import db.realtime as realtime_db
from db import deps
import math
from helpers.iota import iota_helper
from datetime import timedelta


class CrowdFlowsMunicipalityLoad:

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


    def __get_datamodel_apikey_resource(
        self, tenant: str, scope: str, datamodel: str
    ) -> Tuple[str, str]:
        """
        As it says, just get the apikey for a data model from a given tenant and scope,
        using the Aether Link.
        returns a tuple (apikey, resource)
        """

        services = aether_link_helper.get_iota_services(tenant, scope, datamodel)

        if not services or len(services) == 0:
            raise Exception(
                f"Error getting service for params tenant: {tenant}, scope: {scope}, datamodel: {datamodel}"
            )

        if len(services) > 1:
            logging.warning(
                f"More than one iota service found for params tenant: {tenant}, scope: {scope}, datamodel: {datamodel}"
            )

        service = services[0]
        apikey = service.get("apikey")
        resource = service.get("resource")

        if not apikey:
            raise Exception(
                f"Error getting apikey for params tenant: {tenant}, scope: {scope}, datamodel: {datamodel}"
            )

        if not resource:
            raise Exception(
                f"Error getting resource for params tenant: {tenant}, scope: {scope}, datamodel: {datamodel}"
            )

        return apikey, resource

    def __get_user_apikey_resource(
        self, user_id: int, datamodel: str, main_db: Session
    ) -> Tuple[str, str]:
        """
        Gets the apikey of the user for the given data model
        returns a tuple (apikey, resource)
        """

        scope_id = crud_preferences.get_user_preference(
            user_id=user_id,
            preference_name=PreferenceType.PLATFORM_DATA_SCOPE,
            db=main_db,
        )

        if not scope_id:
            raise Exception(
                f"User {user_id} has no scope preference, cannot get apikey"
            )

        tenant, scope = crud_tenant_scope.get_tenant_scope(scope_id, main_db)

        if not scope:
            raise Exception(
                f"Scope {scope_id} not found in the database, cannot get apikey"
            )

        return self.__get_datamodel_apikey_resource(
            tenant=tenant, scope=scope, datamodel=datamodel
        )

    def __send_to_iota(self):
        """
        Function to send the processed data to IOTA
        """
        try:
            apikey, resource = self.__get_user_apikey_resource(
                user_id=self.user_id,
                datamodel="CrowdFlowEventETL",
                main_db=self.main_db,
            )

            for data in self.iota_payload:
                try:
                    logging.info(
                        f"Sending data to iot agent for entity {data['entityId']}"
                    )

                    entity_id = data["entityId"]

                    payload = {
                        k: v
                        for k, v in data.items()
                        if (k != "entityId")
                        and (v is not None)
                        and (not ((isinstance(v, float) and math.isnan(v))))
                    }

                    # params = {"k": apikey, "i": entity_id}


                    # urn:ngsi-ld:Datamodel:id
                    iota_helper.publish_data(
                        id=entity_id,
                        apikey=apikey,
                        resource=resource,
                        body=payload,
                    )
                    # response = self.http_session.post(
                    #     url=resource,
                    #     params=params,
                    #     json=payload,
                    #     headers={"Content-Type": "application/json"},
                    # )
                    # response.raise_for_status()

                except Exception as e:
                    logging.error(f"Error sending data to iot agent: {e}")

        except Exception as e:
            logging.error(f"Error getting apikey and resource: {e}")
            return

    def __get_entity_id_from_urn(self, urn: str) -> str:
        """
        Function to get the entity id from the urn
        """
        return urn.split(":")[-1]

    def __generate_entity_payload(self, data: dict) -> dict:
        payload = []

        flow_entity_urns = []
        flow_ids = []

        sensors_by_urn = {e.urn: e for e in self.entities}

        for flow in data:
            flow_origin_id = self.__get_entity_id_from_urn(flow["origin"])
            flow_destination_id = self.__get_entity_id_from_urn(flow["destination"])

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
                "TimeInstant": self.start_date.isoformat(),
                "startDate": self.start_date.isoformat(),
                "endDate": self.end_date.isoformat(),
            }

            if self.use_classification:
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
                    else self.__get_entity_id_from_urn(flow["origin"])
                )
                dest_name = (
                    dest_sensor.name
                    if dest_sensor and dest_sensor.name
                    else self.__get_entity_id_from_urn(flow["destination"])
                )

                if flow["origin"] == flow["destination"]:
                    name = origin_name
                else:
                    name = f"From {origin_name} to {dest_name}"
                new_flow["name"] = name

            payload.append(new_flow)

        return payload

    def __process_to_fiware(self, df: pd.DataFrame) -> dict:
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
        }

        if self.use_classification:
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
        self.iota_payload = self.__generate_entity_payload(js)

        return self.iota_payload

    def load(self):
        if not self.result.empty:
            if self.mode == "tourism":
                self.__process_to_fiware(self.result)
                self.__send_to_iota()

            else:
                logging.error(f"Mode not supported: {self.mode}")

                return False
        else:
            logging.error("No data to upload")

        return True
