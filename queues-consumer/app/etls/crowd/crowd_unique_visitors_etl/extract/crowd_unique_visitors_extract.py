import ast
import pandas as pd
from config.logging import appLogging as logging
import helpers.aether_link.aether_link_helper as aether_link_helper
from sqlalchemy.orm import Session
from schemas.crowd_unique_visitors_request_schema import (
    CrowdUniqueVisitorsRequest,
)
import db.realtime as realtime_db
from db import deps
from models.crud.crud_crowd_visitors import get_user_crowd_visitor
from helpers.crowd.crowd_utils import crowd_row_processing_lambda, crowd_df_columns_rename
from datetime import timedelta, datetime 
from dateutil.relativedelta import relativedelta

class UniqueVisitorsExtract:

    def __init__(
        self,
        request: CrowdUniqueVisitorsRequest,
        main_db: Session = next(deps.get_db()),
        realtime_db: Session = next(realtime_db.get_db_realtime()),
    ):
        self.processed_info = None
        self.df_raw = None
        self.entities = request.entities
        self.end_date = request.end_date
        self.main_db = main_db
        self.realtime_db = realtime_db
        self.user_id = request.user_id
        self.aggregation_mode = request.aggregation_mode  # Normalize input
        self.entities_tenant_and_scope = [self.entities[0].tenant, self.entities[0].scope]
        

    def timeseries_response_to_dataframe(self):
        """
        Function to convert timeseries response to dataframe
        """
        df = aether_link_helper.get_time_series_in_df_format(self.timeseries_request, df_live_row_processing_lambda=crowd_row_processing_lambda,skip_aether=True)
        
        if df.empty:
            logging.error("No data to work with")
            return None

        return crowd_df_columns_rename(df, municipality=False, random=False, period=False, visitor_type=False)

    def __get_timeseries_variables(self):
        """
        Function to get the variables from the timeseries API
        """
        variables = ["visitorid", "visitorId", "cfeBlock"]
        return variables
    
    def get_period_start_from_end(self, period_end_date: datetime) -> datetime:
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

    def build_timeseries_request(self):
        """
        Function to build the request for the timeseries API
        
        Get
            - visitorid
            - cfeBlock

        Between self.start_date and self.end_date
        """
        entity_urns = [entity.urn for entity in self.entities]
        return [
            {
                "device_ids": entity_urns,
                "measure_ids": self.__get_timeseries_variables(),
                "options": {
                    "limit": 200000,
                    "start_date": self.get_period_start_from_end(self.end_date).isoformat(),
                    "end_date": self.end_date.isoformat(),
                    "tenant": self.entities_tenant_and_scope[0],
                    "scope": self.entities_tenant_and_scope[1],
                },
            }
        ]
        

    def __get_data(self):
        self.timeseries_request = self.build_timeseries_request()
      
        self.df_raw = self.timeseries_response_to_dataframe()
        
    def __extract_visitors(self):
        self.__get_data()

        if self.df_raw is None or self.df_raw.empty:
            logging.error("No data to work with.")

            return False
        
        return True


    def extract(self):        
        if not self.__extract_visitors():

            return False

        return {
            "df_raw": self.df_raw,
            "start_date": self.get_period_start_from_end(self.end_date),
            "end_date": self.end_date
        }