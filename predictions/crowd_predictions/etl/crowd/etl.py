

import os

from crowd_predictions.config import settings
from crowd_predictions.etl.base_etl import BaseETL
from crowd_predictions.etl.crowd.extract import CrowdExtract
from crowd_predictions.etl.crowd.transform import CrowdTransform
from crowd_predictions.etl.crowd.load import CrowdLoad
from crowd_predictions.helpers.fiware_targets import target_slug

class CrowdETL(BaseETL):
    def __init__(self):
        # A SUBDIRECTORY PER TARGET, same as etl/predict/etl.py. main.py does not
        # iterate FIWARE_TARGETS today, but the reason applies the moment it does -
        # and a per-target path costs nothing while it does not.
        self.output_dir = os.path.join(settings.fusion().PREDICTIONS_OUTPUT_DIR, target_slug())
        self.extractor = CrowdExtract()
        self.transformer = None
        self.loader = None

    def init_etl(self) -> bool:
        return True

    def extract(self) -> bool:
        return self.extractor.extract()

    def transform(self) -> bool:
        self.transformer = CrowdTransform(
            smartspot_counts=self.extractor.smartspot_counts,
            lidar_zone_counts=self.extractor.lidar_zone_counts,
            output_dir=self.output_dir,
        )
        return self.transformer.transform()

    def load(self) -> bool:
        self.loader = CrowdLoad(csv_files=self.transformer.exported_files)
        return self.loader.load()
