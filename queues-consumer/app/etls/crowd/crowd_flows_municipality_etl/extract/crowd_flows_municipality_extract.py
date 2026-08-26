from config.logging import appLogging as logging
import helpers.aether_link.aether_link_helper as aether_link_helper
from sqlalchemy.orm import Session
from schemas.crowd_flows_municipality_request_schema import (
    CrowdFlowsMunicipalityRequest,
)
import db.realtime as realtime_db
from db import deps
from models.crud.crud_crowd_visitors import get_user_crowd_visitor
from helpers.crowd.crowd_utils import crowd_row_processing_lambda, crowd_df_columns_rename


class CrowdFlowsMunicipalityExtract:

    def __init__(
        self,
        request: CrowdFlowsMunicipalityRequest,
        main_db: Session = next(deps.get_db()),
        realtime_db: Session = next(realtime_db.get_db_realtime()),
    ):
        self.processed_info = None
        self.df_raw = None
        self.entities = request.entities
        self.start_date = request.start_date
        self.end_date = request.end_date
        self.mode = request.mode
        self.main_db = main_db
        self.realtime_db = realtime_db
        self.user_id = request.user_id
        self.visitors = None
        self.use_classification = True
        self.aggregation_mode = request.aggregation_mode  # Normalize input
        self.entities_tenant_and_scope = [self.entities[0].tenant, self.entities[0].scope]

    def __timeseries_response_to_dataframe(self):
        """
        Function to convert timeseries response to dataframe
        """
        df = aether_link_helper.get_time_series_in_df_format(
            self.timeseries_request,
            df_live_row_processing_lambda=crowd_row_processing_lambda,
        )

        if df.empty:
            logging.error("No data to work with")
            return None

        return crowd_df_columns_rename(df)

    def __get_timeseries_variables(self):
        """
        Function to get the variables from the timeseries API
        """

        return ["visitorId", "detectionType", "random", "cfeBlock"]

    def __build_timeseries_request(self):
        """
        Function to build the request for the timeseries API

        Get
            - visitorId
            - detectionType
            - random
            - cfeBlock
            - period (defaults to 5)
            - municipality (defaults to 'NA')

        Between self.start_date and self.end_date


        """
        entity_urns = [entity.urn for entity in self.entities]
        return [
            {
                "device_ids": entity_urns,
                "measure_ids": self.__get_timeseries_variables(),
                "options": {
                    "limit": 200000,
                    "start_date": self.start_date.isoformat(),
                    "end_date": self.end_date.isoformat(),
                    "tenant": self.entities_tenant_and_scope[0],
                    "scope": self.entities_tenant_and_scope[1],
                },
            }
        ]

    def __get_data(self):
        self.timeseries_request = self.__build_timeseries_request()

        self.df_raw = self.__timeseries_response_to_dataframe()

    def __extract_visitors(self):
        self.__get_data()

        if self.df_raw is None or self.df_raw.empty:
            logging.error("No data to work with")

            return False

        self.visitors = self.df_raw["visitorid"].unique()

        self.previous_visitors = get_user_crowd_visitor(self.main_db, self.user_id)

        self.previous_visitor_types = {
            visitor.visitor_id: visitor.visitor_type
            for visitor in self.previous_visitors
        }

        return True

    def extract(self):
        if self.mode == "tourism":
            if not self.__extract_visitors():
                return False
        else:
            logging.error("Flow mode not supported")
            return False

        return {
            "df_raw": self.df_raw,
            "visitors": self.visitors,
            "previous_visitor_types": self.previous_visitor_types,
        }
