import pandas as pd
from typing import Tuple
from config.logging import appLogging as logging
import helpers.aether_link.aether_link_helper as aether_link_helper
from models.preferences_model import PreferenceType
import models.crud.crud_tenant_scope as crud_tenant_scope
import models.crud.crud_preferences as crud_preferences
from sqlalchemy.orm import Session
from schemas.crowd_unique_visitors_request_schema import (
    CrowdUniqueVisitorsRequest,
)
import db.realtime as realtime_db
from db import deps
import math
from helpers.iota import iota_helper
from datetime import timedelta, datetime 
from dateutil.relativedelta import relativedelta


class UniqueVisitorsLoad:

    def __init__(
        self,
        request: CrowdUniqueVisitorsRequest,
        transform_output: dict,
        main_db: Session = next(deps.get_db()),
        realtime_db: Session = next(realtime_db.get_db_realtime()),
    ):
        # DB Sessions
        self.main_db = main_db
        self.realtime_db = realtime_db

        # Transform Output
        self.result = transform_output["result"]
        self.new_visitor_counts = transform_output["new_visitor_counts"]

        # Request
        self.aggregation_mode = request.aggregation_mode
        self.entities = request.entities
        self.end_date = request.end_date
        self.user_id = request.user_id

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

    def send_to_iota(self):
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
                                f"Sending data to iot agent for entity {data['entityId']} for period {data['startDate']} to {data['endDate']}"
                                )

                    entity_id = data["entityId"]

                    # unset entity_id from the data to avoid conflicts with the id in the body
                    data_to_send = {
                        k: v
                        for k, v in data.items()
                        if (k != "entityId")
                        and (v is not None)
                        and (not ((isinstance(v, float) and math.isnan(v))))
                    }

                    logging.info(f"Data to send for entity {entity_id}: {data_to_send}")

                    # urn:ngsi-ld:Datamodel:id
                    iota_helper.publish_data(
                        id=entity_id,
                        apikey=apikey,
                        resource=resource,
                        body=data_to_send,
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
    
    def __get_period_start_from_end(self, period_end_date: datetime) -> datetime:
        """
        Get period start based on end date and aggregation mode.
        """
        calc_start = None
        if self.aggregation_mode == 'Daily':
            calc_start = period_end_date - timedelta(days=1)
        elif self.aggregation_mode == 'Weekly':
            calc_start = period_end_date - timedelta(weeks=1)
        elif self.aggregation_mode == 'Biweekly':
            calc_start = period_end_date - timedelta(weeks=2)
        elif self.aggregation_mode == 'Monthly':
            calc_start = period_end_date - relativedelta(months=1)
        else:
            raise ValueError("Invalid Aggregation Mode")
        
        return calc_start

    def __generate_entity_payload(self, data: dict) -> dict:
        payload = []

        key_name = f"uniqueVisitors{self.aggregation_mode}"
        for entity_row in data:

            period_end = entity_row["period_date"] 

            if isinstance(period_end, pd.Timestamp):
                period_end = period_end.to_pydatetime()
            
            period_start = self.__get_period_start_from_end(period_end)
            
            new_data = {
                "entityId": self.__get_entity_id_from_urn(entity_row["entity"]),
                f"uniqueVisitors{self.aggregation_mode}": entity_row.get(key_name, 0),
                f"newUniqueVisitors{self.aggregation_mode}": self.new_visitor_counts.get('newUniqueVisitors', 0),
                f"newResidentUniqueVisitors{self.aggregation_mode}": self.new_visitor_counts.get('newResidentUniqueVisitors', 0),
                f"newTouristUniqueVisitors{self.aggregation_mode}": self.new_visitor_counts.get('newTouristUniqueVisitors', 0),
                "TimeInstant": period_end.isoformat(),
                "startDate": period_start.isoformat(),
                "endDate": period_end.isoformat(),
            }

            payload.append(new_data)

        return payload

    def process_to_fiware(self, df: pd.DataFrame) -> dict:
        """
        Function to process data to Fiware and returns a json
        """
        # Rename columns to match required JSON format
        mapping = {
            "entityid": "entity",
            "unique_visitors": f"uniqueVisitors{self.aggregation_mode}",
            "new_unique_visitors": f"newUniqueVisitors{self.aggregation_mode}",
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
            self.process_to_fiware(self.result)
            self.send_to_iota()
        else:
            logging.error("No data to upload")

        return True
