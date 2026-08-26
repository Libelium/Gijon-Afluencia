from etls.base_etl import BaseETL
from config.logging import appLogging as logging
from sqlalchemy.orm import Session
from db import deps
import db.realtime as realtime_db
from etls.crowd.crowd_process_visitors_etl.extract.crowd_process_visitors_extract import (
    ProcessVisitorsExtract,
)
from etls.crowd.crowd_process_visitors_etl.transform.crowd_process_visitors_transform import (
    ProcessVisitorsTransform,
)
from etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load import (
    ProcessVisitorsLoad,
)
from schemas.crowd_process_visitors_request_schema import (
    ProcessVisitorsRequest,
)


class CrowdProcessVisitorsETL(BaseETL):

    def __init__(
        self,
        request: ProcessVisitorsRequest,
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
        logging.info("ETL ProcessVisitorsETL - init")

        return True

    def extract(self):
        logging.info("ETL ProcessVisitorsETL - extract")

        extractor = ProcessVisitorsExtract(
            request=self.request, main_db=self.main_db, realtime_db=self.realtime_db
        )

        self.extract_output = extractor.extract()

        if not self.extract_output:
            return False

        self.main_db.close()

        return True

    def transform(self):
        logging.info("ETL ProcessVisitorsETL - transform")

        transformer = ProcessVisitorsTransform(
            request=self.request,
            extract_output=self.extract_output,
            main_db=self.main_db,
            realtime_db=self.realtime_db,
        )

        self.transform_output = transformer.transform()

        if not self.transform_output:
            return False

        return True

    def load(self):
        logging.info("ETL ProcessVisitorsETL - load")

        loader = ProcessVisitorsLoad(
            request=self.request,
            transform_output=self.transform_output,
            main_db=self.main_db,
            realtime_db=self.realtime_db,
        )

        if not loader.load():
            return False

        return True


# if __name__ == "__main__":
#     etl = ProcessVisitorsETL()
#     etl.execute()
#     exit(0)
