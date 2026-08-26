from etls.base_etl import BaseETL
from config.logging import appLogging as logging
from sqlalchemy.orm import Session
from etls.crowd.crowd_unique_visitors_etl.extract.crowd_unique_visitors_extract import UniqueVisitorsExtract
from etls.crowd.crowd_unique_visitors_etl.transform.crowd_unique_visitors_transform import UniqueVisitorsTransform
from etls.crowd.crowd_unique_visitors_etl.load.crowd_unique_visitors_load import UniqueVisitorsLoad
from schemas.crowd_unique_visitors_request_schema import (
    CrowdUniqueVisitorsRequest
)
import db.realtime as realtime_db
from db import deps

class CrowdUniqueVisitorsETL(BaseETL):

    def __init__(
        self,
        request: CrowdUniqueVisitorsRequest,
        main_db: Session = next(deps.get_db()),
        realtime_db: Session = next(realtime_db.get_db_realtime()),
    ):
        # Request
        self.request = request
        
        # Outputs
        self.extract_output: dict = None
        self.transform_output: dict = None
        
        # DB Sessions
        self.main_db = main_db
        self.realtime_db = realtime_db

    def init_etl(self):
        logging.info("ETL UniqueVisitorsETL - init")

        return True

    def extract(self):
        logging.info("ETL UniqueVisitorsETL - extract")
        
        extractor = UniqueVisitorsExtract(
            request=self.request,
            main_db=self.main_db,
            realtime_db=self.realtime_db
        )

        self.extract_output = extractor.extract()

        if not self.extract_output:
            return False

        return True

    def transform(self):
        logging.info("ETL UniqueVisitorsETL - transform")

        transformer = UniqueVisitorsTransform(
            request=self.request,
            extract_output=self.extract_output,
            main_db=self.main_db,
            realtime_db=self.realtime_db
        )
        
        self.transform_output = transformer.transform()
        
        if not self.transform_output:
            return False

        return True

    def load(self):
        logging.info("ETL UniqueVisitorsETL - load")

        loader = UniqueVisitorsLoad(
            request=self.request,
            transform_output=self.transform_output,
            main_db=self.main_db,
            realtime_db=self.realtime_db
        )
        
        if not loader.load():
            return False

        return True
