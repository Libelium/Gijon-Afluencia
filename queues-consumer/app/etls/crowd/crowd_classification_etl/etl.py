from sqlalchemy.orm import Session
from etls.base_etl import BaseETL
import datetime
import pandas as pd
from config.config import settings
from config.logging import appLogging as logging
import helpers.aether_link.aether_link_helper as aether_link_helper
from schemas.crowd_classification_request_schema import CrowdClassificationRequest
import db.realtime as realtime_db
from db import deps
from models.crud.crud_crowd_visitors import (
    get_user_crowd_visitor,
    create_or_update_crowd_visitors_batch,
)
from helpers.crowd.crowd_utils import (
    crowd_row_processing_lambda,
    crowd_df_columns_rename,
    aggregate_visitor_days,
    merge_visitor_days,
    classify_visitor_days,
)

# Merge pending window summaries every N windows to bound memory.
WINDOWS_PER_MERGE = 24


class CrowdClassificationETL(BaseETL):

    def __init__(
        self,
        request: CrowdClassificationRequest,
        main_db: Session = next(deps.get_db()),
        realtime_db: Session = next(realtime_db.get_db_realtime()),
    ):
        self.processed_info = None
        self.visitor_days = None
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

    def __timeseries_response_to_dataframe(self, timeseries_request):
        """
        Function to convert timeseries response to dataframe
        """
        df = aether_link_helper.get_time_series_in_df_format(
            timeseries_request,
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

    def __build_timeseries_request(self, start_date, end_date):
        """
        Function to build the request for the timeseries API

        Get
            - visitorId
            - detectionType
            - random
            - cfeBlock
            - period (defaults to 5)
            - municipality (defaults to 'NA')

        Between start_date and end_date


        """
        entity_urns = [entity.urn for entity in self.entities]
        return [
            {
                "device_ids": entity_urns,
                "measure_ids": self.__get_timeseries_variables(),
                "options": {
                    "limit": 200000,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "tenant": self.entities_tenant_and_scope[0],
                    "scope": self.entities_tenant_and_scope[1],
                },
            }
        ]

    def __get_windows(self):
        """Yields consecutive [start, end) windows of CROWD_CLASSIFICATION_BATCH_HOURS."""
        step = datetime.timedelta(hours=max(settings.CROWD_CLASSIFICATION_BATCH_HOURS, 1))
        window_start = self.start_date

        while window_start < self.end_date:
            window_end = min(window_start + step, self.end_date)
            yield window_start, window_end
            window_start = window_end

    def __get_visitor_days(self):
        """Streams the cache window by window, keeping only per-visitor/day summaries."""
        pending = []
        windows_with_data = 0

        for window_start, window_end in self.__get_windows():
            df = self.__timeseries_response_to_dataframe(
                self.__build_timeseries_request(window_start, window_end)
            )

            if df is None or df.empty:
                continue

            windows_with_data += 1
            pending.append(aggregate_visitor_days(df))
            del df

            if len(pending) >= WINDOWS_PER_MERGE:
                pending = [merge_visitor_days(pending)]

        logging.info(
            f"Classification data read for user {self.user_id}: "
            f"{windows_with_data} windows with data between {self.start_date} and {self.end_date}"
        )

        return merge_visitor_days(pending)

    def __extract_visitors(self):
        self.visitor_days = self.__get_visitor_days()

        if self.visitor_days is None or self.visitor_days.empty:
            logging.error("No data to work with")
            return False

        self.visitors = self.visitor_days["visitorid"].unique()
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

    def __calculate_visitor_class(self):
        """Classifies over the whole period (Resident needs >2 distinct days)."""

        self.classified_visitors = classify_visitor_days(
            self.visitor_days, self.previous_visitor_types
        )

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
