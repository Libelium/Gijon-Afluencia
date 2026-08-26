import os

from crowd_predictions.config import settings
from crowd_predictions.etl.base_etl import BaseETL
from crowd_predictions.etl.predict.extract import PredictExtract
from crowd_predictions.etl.predict.transform import PredictTransform
from crowd_predictions.etl.predict.load import PredictLoad
from crowd_predictions.helpers.fiware_targets import target_slug

class PredictETL(BaseETL):
    def __init__(self, output_dir: str = None):
        base_dir = output_dir or settings.prediction().PREDICTIONS_FORECAST_OUTPUT_DIR
        # A SUBDIRECTORY PER TARGET, always: sharing it would mix one target's CSVs
        # with the next one's. The slug comes from the environment, i.e. from the
        # active `with fiware_target(...)`.
        self.output_dir = os.path.join(base_dir, target_slug())
        self.extractor = PredictExtract()
        self.transformer = None
        self.loader = None

    def init_etl(self) -> bool:
        return True

    def extract(self) -> bool:
        return self.extractor.extract()

    def transform(self) -> bool:
        self.transformer = PredictTransform(
            history_bins=self.extractor.history_bins,
            model=self.extractor.model,
            train_columns=self.extractor.train_columns,
            metrics=self.extractor.metrics,
            output_dir=self.output_dir,
        )
        return self.transformer.transform()

    def load(self) -> bool:
        self.loader = PredictLoad(csv_files=self.transformer.exported_files)
        return self.loader.load()
