from config.logging import appLogging as logging
from sqlalchemy.orm import Session
from schemas.crowd_data_cache_etl_request_schema import (
    CrowdDataCacheETLRequest,
)
import db.realtime as realtime_db
from db import deps


class CrowdDataCacheTransform:

    def __init__(
        self,
        request: CrowdDataCacheETLRequest,
        extract_output: dict,
        main_db: Session = next(deps.get_db()),
        realtime_db: Session = next(realtime_db.get_db_realtime()),
    ):
        # DB connections
        self.main_db = main_db
        self.realtime_db = realtime_db

        # Extract output
        self.response = extract_output["timeseries_response"]
        self.df_by_entity = extract_output["df_by_entity"]
        self.variables = extract_output["variables"]

        # Request
        self.request = request
        self.entities_by_urn = {entity.urn: entity for entity in self.request.entities}

    def __process_timeseries_data(self):
        """
        Process the timeseries data to extract relevant information.
        """
        logging.info("Processing timeseries data...")
        self.result = []

        start_str = self.request.start_date.strftime("%Y-%m-%dT%H_%M_%S")
        end_str = self.request.end_date.strftime("%Y-%m-%dT%H_%M_%S")

        filename = f"{start_str}_to_{end_str}.csv"

        for urn, df_entity in self.df_by_entity.items():
            logging.info(f"Processing entity {urn}...")

            entity = self.entities_by_urn.get(urn)
            if not entity:
                logging.warning(f"No metadata found for entity {urn}, skipping.")
                continue

            # If the scope is '/', we need to replace it to avoid issues with file paths.
            clear_scope = entity.scope.replace("/", "_")
            urn_split = urn.split(":")[-1]

            s3_prefix = (
                f"data_cache/crowd/{entity.tenant}/{clear_scope}/{urn_split}/{filename}"
            )

            self.result.append(
                {
                    "urn": urn,
                    "df": df_entity,
                    "s3_prefix": s3_prefix,
                    "filename": filename,
                    "tenant": entity.tenant,
                    "scope": clear_scope,
                    "urn_split": urn_split,
                }
            )

    def transform(self):
        self.__process_timeseries_data()

        return {
            "result": self.result,
            "variables": self.variables,
        }
