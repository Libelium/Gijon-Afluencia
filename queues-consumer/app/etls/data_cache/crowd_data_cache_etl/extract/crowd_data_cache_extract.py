from helpers.crowd.crowd_utils import crowd_row_processing_lambda
from config.logging import appLogging as logging
import helpers.aether_link.aether_link_helper as aether_link_helper
from sqlalchemy.orm import Session
from schemas.crowd_data_cache_etl_request_schema import (
    CrowdDataCacheETLRequest,
)
import db.realtime as realtime_db
from db import deps


class CrowdDataCacheExtract:

    def __init__(
        self,
        request: CrowdDataCacheETLRequest,
        main_db: Session = next(deps.get_db()),
        realtime_db: Session = next(realtime_db.get_db_realtime()),
    ):
        self.entities = request.entities
        self.start_date = request.start_date
        self.end_date = request.end_date
        self.main_db = main_db
        self.realtime_db = realtime_db
        self.user_id = request.user_id
        self.example_extract_output = []

    def __get_variables_renames(self):
        """
        Function to get the variables renames for the timeseries API
        """
        return {
            "r_cfe_random": "israndommac",
            "r_cfe_visitorId": "visitorid",
            "r_cfe_detectType": "detectiontype",
            "r_cfe_timeinstant": "timeinstant",
            "r_cfe_rssi": "rssi",
            "r_cfe_ssid": "ssid",
            "r_cfe_signature": "signature",
        }

    def __get_timeseries_variables(self):
        """
        Function to get the variables from the timeseries API
        """

        return [
            "visitorId",
            "detectionType",
            "random",
            "rssi",
            "ssid",
            "signature",
            "period",
            "cfeBlock",
        ]

    def __build_timeseries_request(self):
        """
        Function to build the request for the timeseries API

        Between self.start_date and self.end_date


        """
        return [
            {
                "device_ids": [entity.urn],
                "measure_ids": self.__get_timeseries_variables(),
                "options": {
                    "limit": 200000,
                    "start_date": self.start_date.isoformat(),
                    "end_date": self.end_date.isoformat(),
                    "tenant": entity.tenant,
                    "scope": entity.scope,
                },
            }
            for entity in self.entities
        ]

    def __get_timeseries(self):
        """
        Function to request the timeseries API
        """
        return aether_link_helper.get_time_series(self.timeseries_request)

    def __timeseries_response_to_dataframe(self):
        """
        Convert the timeseries response to a pandas DataFrame.
        """
        return aether_link_helper.time_series_to_df(self.timeseries_response)

    def __get_data(self):
        try:
            self.timeseries_request = self.__build_timeseries_request()
            self.timeseries_response = self.__get_timeseries()
            self.df_raw = self.__timeseries_response_to_dataframe()
            self.df_raw = crowd_row_processing_lambda(self.df_raw, self.__get_variables_renames())
            self.df_by_entity = {
                entity_id: df_group
                for entity_id, df_group in self.df_raw.groupby("entityId")
            }
            logging.info(f"Extracted {len(self.df_raw)} records from timeseries API")

            return True
        except Exception as e:
            logging.error(f"Error fetching timeseries data: {e}")
            return False

    def extract(self):
        if not self.__get_data():
            return False

        return {
            "timeseries_response": self.timeseries_response,
            "df_by_entity": self.df_by_entity,
            "variables": self.__get_timeseries_variables(),
        }
