import pandas as pd
from typing import Tuple
from config.logging import appLogging as logging
import helpers.aether_link.aether_link_helper as aether_link_helper
from models.preferences_model import PreferenceType
import models.crud.crud_tenant_scope as crud_tenant_scope
import models.crud.crud_preferences as crud_preferences
from sqlalchemy.orm import Session
from schemas.crowd_process_visitors_request_schema import (
    ProcessVisitorsRequest,
)
import db.realtime as realtime_db
from db import deps
import math
from helpers.iota import iota_helper
from datetime import timedelta


class ProcessVisitorsLoad:

    def __init__(
        self,
        request: ProcessVisitorsRequest,
        transform_output: dict,
        main_db: Session,
        realtime_db: Session,
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
                f"More than one iota service found for params tenant: "
                + f"{tenant}, scope: {scope}, datamodel: {datamodel}"
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

                    # urn:ngsi-ld:Datamodel:id
                    iota_helper.publish_data(
                        id=entity_id,
                        apikey=apikey,
                        resource=resource,
                        body=payload,
                    )

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

        for flow in data:
            flow_entity_id = self.__get_entity_id_from_urn(flow["entity"])

            flow_id = f"{flow_entity_id}"

            new_flow = {
                "entityId": flow_id,
                "averageVisitDuration": (
                    flow["averageVisitDuration"].total_seconds()
                    if isinstance(flow["averageVisitDuration"], timedelta)
                    else None
                ),
                "minimumVisitDuration": (
                    flow["minimumVisitDuration"].total_seconds()
                    if isinstance(flow["minimumVisitDuration"], timedelta)
                    else None
                ),
                "maximumVisitDuration": (
                    flow["maximumVisitDuration"].total_seconds()
                    if isinstance(flow["maximumVisitDuration"], timedelta)
                    else None
                ),
                "visits": flow["visits"] if flow["visits"] else 0,
                "uniqueVisitors": (
                    flow["uniqueVisitors"] if flow["uniqueVisitors"] else 0
                ),
                "TimeInstant": self.start_date.isoformat(),
                "startDate": self.start_date.isoformat(),
                "endDate": self.end_date.isoformat(),
            }

            if self.use_classification:
                new_flow = {
                    "entityId": flow_id,
                    "averageVisitDuration": (
                        flow["averageVisitDuration"].total_seconds()
                        if isinstance(flow["averageVisitDuration"], timedelta)
                        else None
                    ),
                    "minimumVisitDuration": (
                        flow["minimumVisitDuration"].total_seconds()
                        if isinstance(flow["minimumVisitDuration"], timedelta)
                        else None
                    ),
                    "maximumVisitDuration": (
                        flow["maximumVisitDuration"].total_seconds()
                        if isinstance(flow["maximumVisitDuration"], timedelta)
                        else None
                    ),
                    "visits": flow["visits"] if flow["visits"] else 0,
                    "uniqueVisitors": (
                        flow["uniqueVisitors"] if flow["uniqueVisitors"] else 0
                    ),
                    "touristAverageVisitDuration": (
                        flow["touristAverageVisitDuration"].total_seconds()
                        if isinstance(flow["touristAverageVisitDuration"], timedelta)
                        else None
                    ),
                    "touristMinimumVisitDuration": (
                        flow["touristMinimumVisitDuration"].total_seconds()
                        if isinstance(flow["touristMinimumVisitDuration"], timedelta)
                        else None
                    ),
                    "touristMaximumVisitDuration": (
                        flow["touristMaximumVisitDuration"].total_seconds()
                        if isinstance(flow["touristMaximumVisitDuration"], timedelta)
                        else None
                    ),
                    "touristVisits": (
                        flow["touristVisits"] if flow["touristVisits"] else 0
                    ),
                    "touristUniqueVisitors": (
                        flow["touristUniqueVisitors"]
                        if flow["touristUniqueVisitors"]
                        else 0
                    ),
                    "residentAverageVisitDuration": (
                        flow["residentAverageVisitDuration"].total_seconds()
                        if isinstance(flow["residentAverageVisitDuration"], timedelta)
                        else None
                    ),
                    "residentMinimumVisitDuration": (
                        flow["residentMinimumVisitDuration"].total_seconds()
                        if isinstance(flow["residentMinimumVisitDuration"], timedelta)
                        else None
                    ),
                    "residentMaximumVisitDuration": (
                        flow["residentMaximumVisitDuration"].total_seconds()
                        if isinstance(flow["residentMaximumVisitDuration"], timedelta)
                        else None
                    ),
                    "residentVisits": (
                        flow["residentVisits"] if flow["residentVisits"] else 0
                    ),
                    "residentUniqueVisitors": (
                        flow["residentUniqueVisitors"]
                        if flow["residentUniqueVisitors"]
                        else 0
                    ),
                    "shortTermVisitorAverageVisitDuration": (
                        flow["shortTermVisitorAverageVisitDuration"].total_seconds()
                        if isinstance(
                            flow["shortTermVisitorAverageVisitDuration"], timedelta
                        )
                        else None
                    ),
                    "shortTermVisitorMinimumVisitDuration": (
                        flow["shortTermVisitorMinimumVisitDuration"].total_seconds()
                        if isinstance(
                            flow["shortTermVisitorMinimumVisitDuration"], timedelta
                        )
                        else None
                    ),
                    "shortTermVisitorMaximumVisitDuration": (
                        flow["shortTermVisitorMaximumVisitDuration"].total_seconds()
                        if isinstance(
                            flow["shortTermVisitorMaximumVisitDuration"], timedelta
                        )
                        else None
                    ),
                    "shortTermVisitorVisits": (
                        flow["shortTermVisitorVisits"]
                        if flow["shortTermVisitorVisits"]
                        else 0
                    ),
                    "shortTermVisitorUniqueVisitors": (
                        flow["shortTermVisitorUniqueVisitors"]
                        if flow["shortTermVisitorUniqueVisitors"]
                        else 0
                    ),
                    "TimeInstant": self.start_date.isoformat(),
                    "startDate": self.start_date.isoformat(),
                    "endDate": self.end_date.isoformat(),
                }

            payload.append(new_flow)

        return payload

    def __process_to_fiware(self, df: pd.DataFrame) -> dict:
        """
        Function to process data to Fiware and returns a json
        """
        # Rename columns to match required JSON format
        mapping = {
            "entityid": "entity",
            "averagevisitduration": "averageVisitDuration",
            "minimumvisitduration": "minimumVisitDuration",
            "maximumvisitduration": "maximumVisitDuration",
            "visits": "visits",
            "unique_visitors": "uniqueVisitors",
        }

        if self.use_classification:
            mapping = {
                "entityid": "entity",
                "averagevisitduration": "averageVisitDuration",
                "minimumvisitduration": "minimumVisitDuration",
                "maximumvisitduration": "maximumVisitDuration",
                "visits": "visits",
                "touristaveragevisitduration": "touristAverageVisitDuration",
                "touristminimumvisitduration": "touristMinimumVisitDuration",
                "touristmaximumvisitduration": "touristMaximumVisitDuration",
                "touristvisits": "touristVisits",
                "residentaveragevisitduration": "residentAverageVisitDuration",
                "residentminimumvisitduration": "residentMinimumVisitDuration",
                "residentmaximumvisitduration": "residentMaximumVisitDuration",
                "residentvisits": "residentVisits",
                "shorttermvisitoraveragevisitduration": "shortTermVisitorAverageVisitDuration",
                "shorttermvisitorminimumvisitduration": "shortTermVisitorMinimumVisitDuration",
                "shorttermvisitormaximumvisitduration": "shortTermVisitorMaximumVisitDuration",
                "shorttermvisitorvisits": "shortTermVisitorVisits",
                "unique_visitors": "uniqueVisitors",
                "tourist_unique_visitors": "touristUniqueVisitors",
                "resident_unique_visitors": "residentUniqueVisitors",
                "shorttermvisitor_unique_visitors": "shortTermVisitorUniqueVisitors",
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
