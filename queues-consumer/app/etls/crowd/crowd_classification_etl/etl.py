from sqlalchemy.orm import Session
from etls.base_etl import BaseETL
import datetime
import pandas as pd
from config.logging import appLogging as logging
import helpers.aether_link.aether_link_helper as aether_link_helper
from schemas.crowd_classification_request_schema import CrowdClassificationRequest
import db.realtime as realtime_db
from db import deps
from models.crud.crud_crowd_visitors import (
    get_user_crowd_visitor,
    create_or_update_crowd_visitors_batch,
)
import dateutil.parser
from helpers.crowd.crowd_utils import crowd_row_processing_lambda, crowd_df_columns_rename
import os


class CrowdClassificationETL(BaseETL):

    def __init__(
        self,
        request: CrowdClassificationRequest,
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
        self.previous_visitors = None
        self.entities_tenant_and_scope = [self.entities[0].tenant, self.entities[0].scope]

    def init_etl(self):
        logging.info("ETL CrowdClassificationETL - init")

        return True

    def __timeseries_response_to_dataframe(self):
        """
        Function to convert timeseries response to dataframe
        """
        df = aether_link_helper.get_time_series_in_df_format(
            self.timeseries_request,
            df_live_row_processing_lambda=crowd_row_processing_lambda,
            skip_aether=True,
            drop_nan=True,
        )

        if df.empty:
            return df

        return crowd_df_columns_rename(df)


    def __get_timeseries_variables(self):
        """
        Function to get the variables from the timeseries API
        """
        return ["visitorId", "visitorid", "detectionType", "random", "cfeBlock"]

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

    def __store_visitors(self, chunk_size=5000):
        """
        Function to store visitors in the database
        """

        filtered_df = self.classified_visitors[
            self.classified_visitors["visitortype"] != "ShortTermVisitor"
        ]

        total = len(filtered_df)
        logging.info(f"Total visitors to insert: {total}")

        if total == 0:
            return
        # chunk insertion
        for start in range(0, total, chunk_size):
            end = min(start + chunk_size, total)
            chunk = filtered_df.iloc[start:end]

            logging.info(
                f"Inserting chunk from index {start} to {end} "
                f"({len(chunk)} visitors)"
            )

            create_or_update_crowd_visitors_batch(
                self.main_db,
                chunk["visitorid"].tolist(),
                self.user_id,
                chunk["visitortype"].tolist(),
            )

        logging.info("Visitor insertion process completed")

    def __classify_visitors(
        self, df: pd.DataFrame, resident_threshold_days=2, tourist_min_hours=3
    ) -> pd.DataFrame:
        """
        Classifies visitors as 'Resident' or 'Tourist' based on their presence over time.

        Criteria:
        - If a visitor appears on more than 3 different days, they are classified as 'Resident'.
        - If a visitor appears only on 1-2 days but spends more than 6 hours in total, they are classified as 'Tourist'.
        - Otherwise, they are classified as 'ShortTermVisitor' (optional).

        Args:
            df (pd.DataFrame): DataFrame containing visitor records with 'timeinstant' and 'visitorid'.
            resident_threshold_days (int): Threshold clasifiy a visitor as resident
            tourist_min_hours (int): Threshold clasifiy a visitor as tourist


        Returns:
            pd.DataFrame: The input DataFrame with a new column 'visitortype' assigned.
        """

        # Preproces to ensure that timeinstant is in datetime format
        df["timeinstant"] = df["timeinstant"].apply(
            lambda x: dateutil.parser.parse(x) if isinstance(x, str) else x
        )
        # Convert 'timeinstant' to datetime
        df["timeinstant"] = pd.to_datetime(df["timeinstant"])

        # Extract date from timeinstant
        df["date"] = df["timeinstant"].dt.date

        # Compute unique days visited per visitor
        visitor_days = df.groupby("visitorid")["date"].nunique()

        # Compute time spent per visitor per day
        visitor_time_spent = df.groupby(["visitorid", "date"])["timeinstant"].agg(
            ["min", "max"]
        )
        visitor_time_spent["hours_spent"] = (
            visitor_time_spent["max"] - visitor_time_spent["min"]
        ).dt.total_seconds() / 3600

        # Sum the total hours spent by each visitor
        total_hours_spent = visitor_time_spent.groupby("visitorid")["hours_spent"].sum()

        # Classification logic
        def classify_visitor(vid):
            days = visitor_days[vid]
            hours = total_hours_spent.get(
                vid, 0
            )  # Some visitors might not have time data
            prev = self.previous_visitor_types.get(vid, None)

            if (
                days > resident_threshold_days
                or prev == "Resident"
                or prev == "Tourist"
            ):
                return "Resident"
            elif days <= 2 and hours > tourist_min_hours:
                return "Tourist"
            else:
                return "ShortTermVisitor"

        df["visitortype"] = df["visitorid"].map(classify_visitor)

        # Drop temporary 'date' column
        df.drop(columns=["date"], inplace=True)

        self.visitors_df = pd.DataFrame({"visitorid": self.visitors})

        self.visitors_df["visitortype"] = self.visitors_df["visitorid"].map(
            classify_visitor
        )

        return self.visitors_df

    def __calculate_visitor_class(self):
        """
        Function to calculate visitor flows
        """

        self.classified_visitors = self.__classify_visitors(self.df_raw)

        return self.classified_visitors

    def extract(self):
        logging.info("ETL CrowdClassificationETL - extract")

        if self.mode in  ["monthly", "weekly"]:
            if not self.__extract_visitors():
                return False
        else:
            logging.error("Flow mode not supported")

            return False

        self.main_db.close()

        return True

    def transform(self):
        logging.info("ETL CrowdClassificationETL - transform")

        if self.mode in  ["monthly", "weekly"]:
            self.classified_visitors = self.__calculate_visitor_class()
        else:
            logging.error(f"Mode not supported: {self.mode}")

            return False

        return True

    def load(self):
        logging.info("ETL CrowdClassificationETL - load")

        if len(self.classified_visitors) > 0:
            if self.mode in  ["monthly", "weekly"]:
                self.__store_visitors()
            else:
                logging.error(f"Mode not supported: {self.mode}")

                return False

            logging.info("Data uploaded")
        else:
            logging.error("No data to upload")

        return True


# if __name__ == "__main__":
#     etl = CrowdClassificationETL()
#     etl.execute()
#     exit(0)
