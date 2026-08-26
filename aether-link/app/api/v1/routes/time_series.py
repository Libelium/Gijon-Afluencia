from typing import List, Union
from aether_pylib.time_series.time_series_request import TimeSeriesRequest
from aether_pylib.time_series.time_series_response import TimeSeriesResponse
from aether_pylib.time_series.time_series_hash_response import (
    TimeSeriesHashResponse,
)
from aether_pylib.time_series.delete_time_series_request import (
    DeleteTimeSeriesRequest,
)
from aether_pylib.time_series.delete_time_series_response import (
    DeleteTimeSeriesResponse,
)
from fastapi import APIRouter, Header, Request
from typing import Annotated
from app.core.config.config import time_series_data_source
from app.core.config.logging import appLogging as logging
from app.core.config.config import settings

time_series_router = APIRouter()


@time_series_router.post("/")
async def get_time_series(
    request: Request,
    body: List[TimeSeriesRequest],
) -> List[TimeSeriesResponse]:
    """
    Returns the time series requested in the request body
    """
    client_host = request.client.host
    logging.info(f"Client host: {client_host}")

    # transform the request to a list if it is not
    if not isinstance(body, list):
        body = [body]

    return time_series_data_source.get_time_series(body)


@time_series_router.post("/hash")
async def get_time_series_hash(
    request: Request,
    body: List[TimeSeriesRequest],
) -> List[TimeSeriesHashResponse]:
    """
    Returns a deterministic sha256 digest of the rows that the equivalent
    `/time-series` call would return, computed inside the database. Used by
    the blockchain footprint feature to commit a verifiable fingerprint of
    a timeseries query to a public chain without shipping raw data through
    the network.
    """
    client_host = request.client.host
    logging.info(f"Hash request from client host: {client_host}")

    if not isinstance(body, list):
        body = [body]

    return time_series_data_source.get_time_series_hash(body)


@time_series_router.delete("/")
async def delete_time_series(
    request: Request,
    body: List[DeleteTimeSeriesRequest],
) -> List[DeleteTimeSeriesResponse]:
    """
    Deletes the time series requested in the request body
    """
    client_host = request.client.host
    logging.info(f"Client host: {client_host}")

    # transform the request to a list if it is not
    if not isinstance(body, list):
        body = [body]

    return time_series_data_source.delete_time_series(body)
