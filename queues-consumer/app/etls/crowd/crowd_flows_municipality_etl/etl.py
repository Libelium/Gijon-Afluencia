from typing import Optional
from etls.base_etl import BaseETL
from config.logging import appLogging as logging
from sqlalchemy.orm import Session
from etls.crowd.crowd_flows_municipality_etl.extract.crowd_flows_municipality_extract import (
    CrowdFlowsMunicipalityExtract,
)
from etls.crowd.crowd_flows_municipality_etl.transform.crowd_flows_municipality_transform import (
    CrowdFlowsMunicipalityTransform,
)
from etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load import (
    CrowdFlowsMunicipalityLoad,
)
from schemas.crowd_flows_municipality_request_schema import (
    CrowdFlowsMunicipalityRequest,
)
import db.realtime as realtime_db
from db import deps


class CrowdFlowsMunicipalityETL(BaseETL):

    def __init__(
        self,
        request: CrowdFlowsMunicipalityRequest,
        main_db: Session = next(deps.get_db()),
        realtime_db: Session = next(realtime_db.get_db_realtime()),
    ):
        # Request
        self.request = request

        # Outputs
        self.extract_output: Optional[dict] = None
        self.transform_output: Optional[dict] = None

        # DB Sessions
        self.main_db = main_db
        self.realtime_db = realtime_db

    def init_etl(self):
        logging.info("ETL CrowdFlowsMunicipalityETL - init")

        return True

    def extract(self):
        logging.info("ETL CrowdFlowsMunicipalityETL - extract")

        extractor = CrowdFlowsMunicipalityExtract(
            request=self.request, main_db=self.main_db, realtime_db=self.realtime_db
        )

        self.extract_output = extractor.extract()

        if not self.extract_output:
            return False

        self.main_db.close()

        return True

    def transform(self):
        logging.info("ETL CrowdFlowsMunicipalityETL - transform")

        transformer = CrowdFlowsMunicipalityTransform(
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
        logging.info("ETL CrowdFlowsMunicipalityETL - load")

        loader = CrowdFlowsMunicipalityLoad(
            request=self.request,
            transform_output=self.transform_output,
            main_db=self.main_db,
            realtime_db=self.realtime_db,
        )

        if not loader.load():
            return False

        return True


# if __name__ == "__main__":
#     etl = CrowdFlowsMunicipalityETL()
#     etl.execute()
#     exit(0)
