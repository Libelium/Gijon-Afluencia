from config.config import TimeseriesType, settings
from jobs.job import Job
from jobs.timeseries.timescale.timescale_sync_job import TimescaleSyncJob
from schemas.entity_data_notification import EntityDataNotification


class SaveTimeseriesJob(Job):
    """
    This job saves the timeseries data to the configured timeseries backend.
    """

    TYPE_RUNNERS = {
        TimeseriesType.TIMESCALE: lambda entity_data: TimescaleSyncJob(
            entity_data
        ).handle(),
        TimeseriesType.NONE: lambda entity_data: None,
    }

    def __init__(
        self, entity_data: EntityDataNotification, timeseries_type: str = None
    ):
        ts_type = timeseries_type or settings.TIMESERIES_TYPE
        self.runner = self.TYPE_RUNNERS.get(ts_type)

        self.entity_data = entity_data

    def handle(self):
        """
        Just runs the corresponding runner
        """
        return self.runner(self.entity_data)
