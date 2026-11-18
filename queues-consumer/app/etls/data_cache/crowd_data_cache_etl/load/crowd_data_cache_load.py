import os
import pandas as pd
from config.config import storage
from config.config import settings
from config.logging import appLogging as logging
from sqlalchemy.orm import Session
from schemas.crowd_data_cache_etl_request_schema import (
    CrowdDataCacheETLRequest,
)
import db.realtime as realtime_db
import helpers.aether_link.aether_link_helper as aether_link_helper
from helpers.crowd.crowd_utils import append_new_crowd_rows, to_crowd_cache_schema
from db import deps


def _is_not_found(error: Exception) -> bool:
    """True when the storage error means the object does not exist (S3 or MinIO)."""
    code = getattr(error, "code", None)
    response = getattr(error, "response", None) or {}
    code = code or response.get("Error", {}).get("Code")
    return str(code) in ("404", "NoSuchKey", "NotFound")


# Where each hour's CSV is written before it is uploaded.
TEMP_DIR = "/code/temp"

class CrowdDataCacheLoad:

    def __init__(
        self,
        request: CrowdDataCacheETLRequest,
        transform_output: dict,
        main_db: Session = next(deps.get_db()),
        realtime_db: Session = next(realtime_db.get_db_realtime()),
    ):
        # DB Sessions
        self.main_db = main_db
        self.realtime_db = realtime_db

        # Transform Output
        self.result = transform_output["result"]
        self.variables = transform_output["variables"]

        # Request
        self.entities = request.entities
        self.start_date = request.start_date
        self.end_date = request.end_date
        self.user_id = request.user_id

    def __build_delete_timeseries_request(self):
        """
        Function to build the request for the timeseries API

        Between self.start_date and self.end_date


        """
        return [
            {
                "device_ids": [entity.urn],
                "measure_ids": self.variables,
                "options": {
                    "start_date": self.start_date.isoformat(),
                    "end_date": self.end_date.isoformat(),
                    "tenant": entity.tenant,
                    "scope": entity.scope,
                },
            }
            for entity in self.entities
        ]

    def __delete_timeseries(self):
        """
        Function to request the timeseries API
        """
        self.delete_request = self.__build_delete_timeseries_request()

        return aether_link_helper.delete_time_series(self.delete_request)

    def __merge_with_existing(self, df, s3_prefix, filename, tenant, urn_split):
        """
        Adds the rows already cached for this hour, so that re-running an hour
        (late notifications, a forced run) never drops what was cached before.
        Only a missing object counts as "nothing cached": any other storage
        error is raised, so nothing is uploaded nor deleted from Timescale.
        """
        try:
            existing_path = storage.download_file(
                f"existing_{tenant}_{urn_split}_{filename}", s3_prefix
            )
        except Exception as e:
            if _is_not_found(e):
                return df
            raise

        try:
            if os.path.getsize(existing_path) == 0:
                return df
            existing = to_crowd_cache_schema(pd.read_csv(existing_path, low_memory=False))
        finally:
            os.remove(existing_path)

        merged = append_new_crowd_rows(existing, df)
        logging.info(
            f"Added {len(merged) - len(existing)} of {len(df)} rows read to the "
            f"{len(existing)} already cached in {s3_prefix}"
        )
        return merged

    def __store_to_s3(self):
        """
        Function to store the processed data to S3
        """
        success = True
        
        for item in self.result:
            df = item["df"]
            tenant = item["tenant"]
            scope = item["scope"]
            urn_split = item["urn_split"]
            filename = item["filename"]
            s3_prefix = item["s3_prefix"]

            local_dir = f"{TEMP_DIR}/{tenant}/{scope}/{urn_split}"
            os.makedirs(local_dir, exist_ok=True)
            local_path = f"{local_dir}/{filename}"

            try:
                df = self.__merge_with_existing(df, s3_prefix, filename, tenant, urn_split)
                df.to_csv(local_path, index=False)
                storage.upload_file(s3_prefix, local_path)
                logging.info(f"Uploaded {local_path} to S3 as {s3_prefix}")
                os.remove(local_path)
                logging.info(f"Deleted local file: {local_path}")
            except Exception as e:
                logging.error(f"Failed storing file for {item['urn']}: {e}")
                success = False

        return success

    def load(self):
        if len(self.result) > 0:
            if self.__store_to_s3():
                if settings.DATA_CACHE_DELETE_AFTER_UPLOAD:
                    self.__delete_timeseries()
                    logging.info("All files uploaded successfully, deleting timeseries")
                else:
                    logging.info("All files uploaded successfully, NOT deleting timeseries")
            else:
                logging.info("Some files failed to upload, NOT deleting timeseries")
            
        else:
            logging.info("No data to upload")

        return True
