from etls.base_etl import BaseETL
from config.logging import appLogging as logging
from sqlalchemy.orm import Session
from etls.data_cache.crowd_data_cache_etl.extract.crowd_data_cache_extract import (
    CrowdDataCacheExtract,
)
from etls.data_cache.crowd_data_cache_etl.transform.crowd_data_cache_transform import (
    CrowdDataCacheTransform,
)
from etls.data_cache.crowd_data_cache_etl.load.crowd_data_cache_load import (
    CrowdDataCacheLoad,
)
from schemas.crowd_data_cache_etl_request_schema import (
    CrowdDataCacheETLRequest,
)
import db.realtime as realtime_db
from db import deps


class CrowdDataCacheETL(BaseETL):

    def __init__(
        self,
        request: CrowdDataCacheETLRequest,
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
        logging.info("ETL CrowdDataCacheETL - init")

        return True

    def extract(self):
        logging.info("ETL CrowdDataCacheETL - extract")

        extractor = CrowdDataCacheExtract(
            request=self.request, main_db=self.main_db, realtime_db=self.realtime_db
        )

        self.extract_output = extractor.extract()

        if not self.extract_output:
            return False

        return True

    def transform(self):
        logging.info("ETL CrowdDataCacheETL - transform")

        transformer = CrowdDataCacheTransform(
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
        logging.info("ETL CrowdDataCacheETL - load")

        loader = CrowdDataCacheLoad(
            request=self.request,
            transform_output=self.transform_output,
            main_db=self.main_db,
            realtime_db=self.realtime_db,
        )

        if not loader.load():
            return False

        return True
