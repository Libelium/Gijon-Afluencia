from datetime import timedelta
from json import JSONEncoder
import pandas as pd
from typing import List
from aether_pylib.time_series.time_series import TimeSeriesValue
from aether_pylib.time_series.time_series_options import (
    TimeSeriesAggregationOptions,
    TimeSeriesAggregationOptionsType,
)
from app.core.config.logging import appLogging as logging
import re


def __mean(df: pd.Series, interval: timedelta, extra: float) -> pd.DataFrame:
    """
    Calculates the average of the values in the dataframe using the interval
    :df: dataframe with the values to aggregate
    :interval: interval to aggregate
    :time_serieas_aggregation_fill: fill method to use
    :return: dataframe with the aggregated values
    """
    precision_time = pd.to_timedelta("PT1M")
    
    # Remove duplicates, keeping the first occurrence
    df = df[~df.index.duplicated(keep='first')]

    df = df.groupby(df.index).mean()

    return df.resample(precision_time, origin="start").ffill().resample(interval).mean()


def __moving_avg(df: pd.Series, interval: timedelta, extra: float) -> pd.DataFrame:
    """
    Calculates the moving average of the values in the dataframe using the interval
    :df: dataframe with the values to aggregate
    :interval: interval to aggregate
    :return: dataframe with the aggregated values
    """
    # Remove duplicates, keeping the first occurrence
    df = df[~df.index.duplicated(keep='first')]
    
    # resample the dataframe to the interval
    # for some reason, this was the only one that did not work with the timedelta
    return df.rolling(interval).mean()


def __sum(df: pd.Series, interval: timedelta, extra: float) -> pd.DataFrame:
    """
    Calculates the sum of the values in the dataframe using the interval
    :df: dataframe with the values to aggregate
    :interval: interval to aggregate
    :options_fill: fill method to use
    :return: dataframe with the aggregated values
    """
    # Remove duplicates, keeping the first occurrence
    df = df[~df.index.duplicated(keep='first')]
    
    # fill with 0
    return df.resample(interval, origin="start").sum()


def __max(df: pd.Series, interval: int, extra: float) -> pd.DataFrame:
    """
    Calculates the max of the values in the dataframe using the interval
    :df: dataframe with the values to aggregate
    :interval: interval to aggregate
    :options_fill: fill method to use
    :return: dataframe with the aggregated values
    """
    # Remove duplicates, keeping the first occurrence
    df = df[~df.index.duplicated(keep='first')]
    
    # fill na with previous value
    df = df.resample(interval, origin="start").ffill()
    return df.resample(interval).max()


def __min(df: pd.Series, interval: timedelta, extra: float) -> pd.DataFrame:
    """
    Calculates the min of the values in the dataframe using the interval
    :df: dataframe with the values to aggregate
    :interval: interval to aggregate
    :options_fill: fill method to use
    :return: dataframe with the aggregated values
    """
    # Remove duplicates, keeping the first occurrence
    df = df[~df.index.duplicated(keep='first')]
    
    df = df.resample(interval, origin="start").ffill()
    return df.resample(interval).min()


def __percentile(df: pd.Series, interval: timedelta, extra: float) -> pd.DataFrame:
    """
    Calculates the percentile of the values in the dataframe using the interval
    :df: dataframe with the values to aggregate
    :interval: interval to aggregate
    :options_fill: fill method to use
    :extra: percentile value
    :return: dataframe with the aggregated values
    """
    # Remove duplicates, keeping the first occurrence
    df = df[~df.index.duplicated(keep='first')]
    
    return df.resample(interval, origin="start").quantile(extra / 100)


def __time_series_to_pandas_series(time_series: List[TimeSeriesValue]) -> pd.DataFrame:
    """
    Converts a list of TimeSeriesValue to a dataframe
    :time_series: list of TimeSeriesValue to convert
    :return: dataframe with the values
    """

    series = pd.Series(
        [x.value for x in time_series],
        index=[pd.to_datetime(x.timestamp) for x in time_series],
    )

    return series


# map of aggregation types to functions, to simplify the code
__aggregation_map = {
    TimeSeriesAggregationOptionsType.MEAN: __mean,
    TimeSeriesAggregationOptionsType.SUM: __sum,
    TimeSeriesAggregationOptionsType.MAX: __max,
    TimeSeriesAggregationOptionsType.MIN: __min,
    TimeSeriesAggregationOptionsType.MOVING_AVG: __moving_avg,
    TimeSeriesAggregationOptionsType.PERCENTILE: __percentile,
}


def aggregate(
    options: TimeSeriesAggregationOptions, values: List[TimeSeriesValue]
) -> List[TimeSeriesValue]:
    """
    Calculates the aggregated time series values using the aggregation type, interval and fill method
    of options
    :options: TimeSeriesAggregationOptions (aggregation configuration)
    :values: list of TimeSeriesValue to aggregate
    :return: list of TimeSeriesValue (aggregated values)
    """

    # check if there is something to do
    if (
        options is None
        or options.type is None
        or options.interval is None
        or options.interval == 0
        or len(values) == 0
    ):
        return values

    df = __time_series_to_pandas_series(values)

    # sort by timestamp
    df = df.sort_index()

    # apply the aggregation
    if re.match(r"^[a-z]+-\d+$", options.type):
        # for the percentile, we need to extract the number
        func, num = options.type.split("-")
        method = __aggregation_map.get(TimeSeriesAggregationOptionsType(func))
        method_extra = float(num)
    else:
        method = __aggregation_map.get(TimeSeriesAggregationOptionsType(options.type))
        method_extra = None

    if method is None:
        logging.error(
            f"Aggregation type {options.type} not supported, cannot aggregate time series"
        )
        return values

    # resample interpolate linear
    df = method(df, options.interval, method_extra)

    # drop NA
    df = df.dropna()

    # order descending
    df = df.sort_index(ascending=False)

    # convert back to TimeSeriesValue
    time_series_values = []
    for index, value in df.items():
        time_series_values.append(
            TimeSeriesValue(timestamp=index.isoformat(), value=value)
        )

    return time_series_values
