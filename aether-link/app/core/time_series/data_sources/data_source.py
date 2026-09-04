from abc import ABC, abstractmethod
from typing import List
from app.core.configurable_service.configurable_service import ConfigurableService

from aether_pylib.time_series.time_series_request import TimeSeriesRequest
from aether_pylib.time_series.time_series_response import TimeSeriesResponse
from aether_pylib.time_series.delete_time_series_request import (
    DeleteTimeSeriesRequest,
)
from aether_pylib.time_series.delete_time_series_response import (
    DeleteTimeSeriesResponse,
)


class DataSource(ConfigurableService):
    """
    Generic temporal data source
    """

    @abstractmethod
    def get_time_series(self, requests: List[TimeSeriesRequest]) -> TimeSeriesResponse:
        """
        Retrieve time series data from the data source for the given requests. The behavior
        must match the TimeSeriesRequest specification
        """
        pass

    def delete_time_series(
        self, requests: List[DeleteTimeSeriesRequest]
    ) -> DeleteTimeSeriesResponse:
        """
        Delete time series data from the data source for the given requests. The behavior
        must match the DeleteTimeSeriesRequest specification
        """
        raise NotImplementedError(
            "This data source does not support deleting time series data"
        )
