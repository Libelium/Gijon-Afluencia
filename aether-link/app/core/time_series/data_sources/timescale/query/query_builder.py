import re
from datetime import timedelta
from functools import reduce
from typing import Callable, Dict, List, Tuple, Union

from aether_pylib.time_series.time_scope import TimeScope, TimeScopeAdjustment
from aether_pylib.time_series.time_series_options import (
    TimeSeriesAggregationOptions,
    TimeSeriesAggregationOptionsType,
    TimeSeriesOptions,
    TimeSeriesOrdering,
    WhereClause,
    WhereClauseOperation,
)
from aether_pylib.time_series.time_series_request import TimeSeriesRequest
from aether_pylib.time_series.delete_time_series_request import (
    DeleteTimeSeriesRequest,
)
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Select,
    Table,
    Time,
    and_,
    cast,
    extract,
    func,
    literal_column,
    or_,
    delete,
)
from sqlalchemy.orm import Query
from sqlalchemy.sql import over
from sqlalchemy.sql.expression import select
from sqlalchemy.sql.functions import coalesce

import app.core.time_series.data_sources.timescale.constants as ts_constants
import app.core.time_series.data_sources.timescale.models.entity_data_model as edm
from app.core.config.logging import appLogging as logging


def build_query(
    request: TimeSeriesRequest,
    metadata: MetaData,
) -> Select:
    """
    Build a query from a TimeSeriesRequest
    """

    schema = get_request_schema(request)

    entity_data_table = edm.build_entity_data_model(metadata, schema)

    query, ts_column = get_base_select(request.options, entity_data_table)

    ordering = (
        ts_column.desc()
        if request.options.order == TimeSeriesOrdering.DESC
        else ts_column.asc()
    )

    query = query.filter(entity_data_table.c.scope_id == request.options.scope)

    if request.measure_ids is not None and len(request.measure_ids) > 0:
        query = query.filter(entity_data_table.c.attr_id.in_(request.measure_ids))

    if request.device_ids:
        query = query.filter(entity_data_table.c.entity_id.in_(request.device_ids))

    if request.options.start_date:
        query = query.filter(entity_data_table.c.time >= request.options.start_date)

    if request.options.end_date:
        query = query.filter(entity_data_table.c.time <= request.options.end_date)

    query = query.order_by(ordering)

    if request.options.period:
        for period in request.options.period:
            query = apply_period_filter(query, period, entity_data_table.c.time)

    if request.options.limit:
        # TODO: remove row_number from the query result
        query = query.add_columns(
            over(
                func.row_number(),
                partition_by=[
                    entity_data_table.c.entity_id,
                    entity_data_table.c.attr_id,
                ],
                order_by=ordering,
            ).label("row_number"),
        )
        subquery = query.subquery()
        non_aux_cols = [col for col in subquery.columns if col.name != "row_number"]
        query = select(*non_aux_cols).filter(
            subquery.c.row_number <= request.options.limit
        )

    return query


def build_delete_query(
    request: DeleteTimeSeriesRequest,
    metadata: MetaData,
) -> delete:
    """
    Build a delete query from a DeleteTimeSeriesRequest
    """
    schema = get_request_schema(request)
    entity_data_table = edm.build_entity_data_model(metadata, schema)
    query = delete(entity_data_table)

    query = query.filter(entity_data_table.c.scope_id == request.options.scope)

    if request.measure_ids is not None and len(request.measure_ids) > 0:
        query = query.filter(entity_data_table.c.attr_id.in_(request.measure_ids))

    if request.device_ids:
        query = query.filter(entity_data_table.c.entity_id.in_(request.device_ids))

    if request.options.start_date:
        query = query.filter(entity_data_table.c.time >= request.options.start_date)

    if request.options.end_date:
        query = query.filter(entity_data_table.c.time <= request.options.end_date)

    return query


def get_request_schema(
    request: Union[TimeSeriesRequest, DeleteTimeSeriesRequest],
) -> str:
    """
    Get the schema of the request (regular or delete).
    Usually (unless modified): SCHEMA_PREFIX + <tenant>
    """

    tenant = request.options.tenant
    schema_name = f"{ts_constants.SCHEMA_PREFIX}{tenant}"

    return schema_name


def apply_period_filter(query: Query, period: TimeScope, ts_attr: Column) -> Query:
    """
    Apply the period filter to the query
    """

    basic_conditions = []

    # month filtering
    month_conditions = get_month_filtering_condition(period, ts_attr)
    if month_conditions is not None:
        basic_conditions.append(month_conditions)

    # month day filtering
    month_day_conditions = get_month_day_filtering_condition(period, ts_attr)
    if month_day_conditions is not None:
        basic_conditions.append(month_day_conditions)

    # week day filtering
    week_day_conditions = get_week_day_filtering_condition(period, ts_attr)
    if week_day_conditions is not None:
        basic_conditions.append(week_day_conditions)

    # hour filtering
    hour_conditions = get_hour_filtering_condition(period, ts_attr)
    if hour_conditions is not None:
        basic_conditions.append(hour_conditions)

    # merge all basic conditions
    filter_condition = reduce(and_, basic_conditions) if basic_conditions else None

    if period.extra:

        if filter_condition is None:
            filter_condition = True

        for extra in period.extra:
            extra_condition = get_extra_filtering_condition(extra, ts_attr)

            if extra_condition is None:
                continue

            filter_condition = (
                and_(filter_condition, ~extra_condition)
                if extra.exclude
                else or_(filter_condition, extra_condition)
            )

    query = query.filter(filter_condition) if filter_condition is not None else query

    return query


def get_month_filtering_condition(period: TimeScope, ts_attr: Column) -> List:
    """
    Get the month filtering condition
    """
    month_conditions = []
    if period.months:
        for month in period.months:
            month_conditions.append(extract("month", ts_attr) == month)

    return reduce(or_, month_conditions) if month_conditions else None


def get_month_day_filtering_condition(period: TimeScope, ts_attr: Column) -> List:
    """
    Get the month day filtering condition
    """
    month_day_conditions = []
    if period.month_days:
        for month_day in period.month_days:
            month_day_conditions.append(extract("day", ts_attr) == month_day + 1)

    return reduce(or_, month_day_conditions) if month_day_conditions else None


def get_week_day_filtering_condition(period: TimeScope, ts_attr: Column) -> List:
    """
    Get the week day filtering condition
    """
    week_day_conditions = []
    if period.week_days:
        for week_day in period.week_days:
            week_day_conditions.append(extract("dow", ts_attr) == week_day)

    return reduce(or_, week_day_conditions) if week_day_conditions else None


def get_hour_filtering_condition(period: TimeScope, ts_attr: Column) -> List:
    """
    Get the hour filtering condition
    """
    # hour filtering
    hour_conditions = []

    casted_tz_ts_attr = ts_attr.op("AT TIME ZONE")(str(period.timezone))

    if period.hours:
        for hour in period.hours:
            if hour[0] <= hour[1]:
                hour_conditions.append(
                    cast(casted_tz_ts_attr, Time).between(
                        cast(hour[0], Time), cast(hour[1], Time)
                    )
                )
            else:
                hour_conditions.append(
                    or_(
                        cast(casted_tz_ts_attr, Time) >= cast(hour[0], Time),
                        cast(casted_tz_ts_attr, Time) <= cast(hour[1], Time),
                    )
                )

    return reduce(or_, hour_conditions) if hour_conditions else None


def get_extra_filtering_condition(extra: TimeScopeAdjustment, ts_attr: Column) -> List:
    """
    Get the extra filtering condition
    """
    extra_conditions = []
    if extra.year is not None:
        extra_conditions.append(extract("year", ts_attr) == extra.year)

    if extra.month is not None:
        extra_conditions.append(extract("month", ts_attr) == extra.month + 1)

    if extra.month_day is not None:
        extra_conditions.append(extract("day", ts_attr) == extra.month_day + 1)

    return reduce(and_, extra_conditions) if extra_conditions else None


def get_time_bucket_column(interval: timedelta, entity_data_table: Table) -> Column:
    """
    Returns the time bucket column, labeled as "ts"
    """
    return literal_column(
        f"time_bucket('{interval}', {entity_data_table.c.time})"
    ).label("ts")


def get_numeric_value_column(entity_data_table: Table) -> Column:
    """
    Returns the numeric value column
        If the value is a double, return the double value
        If the value is a boolean, return the boolean value casted to integer
    """
    return coalesce(
        entity_data_table.c.attr_double_value,
        entity_data_table.c.attr_boolean_value.cast(Integer),
    )


def filter_numeric_values(base: Select, entity_data_table: Table) -> Select:
    """
    Return the base query with the filter for numeric values (double and boolean)
    """
    return base.filter(
        or_(
            entity_data_table.c.attr_value_type == "double",
            entity_data_table.c.attr_value_type == "boolean",
        )
    )


def get_mean_select(
    base: Select, options: TimeSeriesOptions, entity_data_table: Table
) -> Tuple[Select, Column]:
    """
    Returns the select for the mean aggregation
    """
    ts_col = get_time_bucket_column(options.aggregation.interval, entity_data_table)

    query = base.add_columns(
        ts_col,
        func.avg(
            get_numeric_value_column(entity_data_table),
        ).label("attr_double_value"),
    ).group_by(ts_col, entity_data_table.c.entity_id, entity_data_table.c.attr_id)

    query = filter_numeric_values(query, entity_data_table)

    return query, ts_col


def get_moving_avg_select(
    base: Select, options: TimeSeriesOptions, entity_data_table: Table
) -> Tuple[Select, Column]:
    """
    Returns the select for the moving average aggregation
    """

    ts_col = entity_data_table.c.time.label("ts")

    base_avg = func.avg(get_numeric_value_column(entity_data_table))
    avg_col = literal_column(
        f"{base_avg} OVER (PARTITION BY {entity_data_table.c.entity_id}, {entity_data_table.c.attr_id}"
        + f" ORDER BY {ts_col} RANGE BETWEEN interval '{options.aggregation.interval}' PRECEDING AND CURRENT ROW)"
    )

    query = base.add_columns(
        ts_col,
        avg_col.label("attr_double_value"),
    )

    query = filter_numeric_values(query, entity_data_table)

    return query, ts_col


def get_sum_select(
    base: Select, options: TimeSeriesOptions, entity_data_table: Table
) -> Tuple[Select, Column]:
    """
    Returns the select for the sum aggregation
    """
    ts_col = get_time_bucket_column(options.aggregation.interval, entity_data_table)
    query = base.add_columns(
        ts_col,
        func.sum(get_numeric_value_column(entity_data_table)).label(
            "attr_double_value"
        ),
    ).group_by(ts_col, entity_data_table.c.entity_id, entity_data_table.c.attr_id)

    query = filter_numeric_values(query, entity_data_table)

    return query, ts_col


def get_min_select(
    base: Select, options: TimeSeriesOptions, entity_data_table: Table
) -> Tuple[Select, Column]:
    """
    Returns the select for the min aggregation
    """
    ts_col = get_time_bucket_column(options.aggregation.interval, entity_data_table)
    query = base.add_columns(
        ts_col,
        func.min(
            get_numeric_value_column(entity_data_table),
        ).label("attr_double_value"),
    ).group_by(ts_col, entity_data_table.c.entity_id, entity_data_table.c.attr_id)

    query = filter_numeric_values(query, entity_data_table)

    return query, ts_col


def get_max_select(
    base: Select, options: TimeSeriesOptions, entity_data_table: Table
) -> Tuple[Select, Column]:
    """
    Returns the select for the max aggregation
    """
    ts_col = get_time_bucket_column(options.aggregation.interval, entity_data_table)
    query = base.add_columns(
        ts_col,
        func.max(get_numeric_value_column(entity_data_table)).label(
            "attr_double_value"
        ),
    ).group_by(ts_col, entity_data_table.c.entity_id, entity_data_table.c.attr_id)

    query = filter_numeric_values(query, entity_data_table)

    return query, ts_col


def get_percentile_select(
    base: Select, options: TimeSeriesOptions, entity_data_table: Table
) -> Tuple[Select, Column]:
    """
    Returns the select for the percentile aggregation
    """
    # for the percentile, we need to extract the number
    _, percentile = options.aggregation.type.split("-")
    percentile = float(percentile) / 100.0

    ts_col = get_time_bucket_column(options.aggregation.interval, entity_data_table)

    query = base.add_columns(
        ts_col,
        func.percentile_cont(percentile)
        .within_group(get_numeric_value_column(entity_data_table))
        .label("attr_double_value"),
    ).group_by(ts_col, entity_data_table.c.entity_id, entity_data_table.c.attr_id)

    query = filter_numeric_values(query, entity_data_table)

    return query, ts_col


def get_no_aggr_select(
    base: Select, options: TimeSeriesOptions, entity_data_table: Table
) -> Tuple[Select, Column]:
    """
    Returns the select for the no aggregation
    """
    ts_col = entity_data_table.c.time.label("ts")
    query = base.add_columns(
        ts_col,
        entity_data_table.c.attr_value_type,
        entity_data_table.c.attr_double_value,
        entity_data_table.c.attr_string_value,
        entity_data_table.c.attr_boolean_value,
        entity_data_table.c.attr_json_value,
    )

    return query, ts_col


__aggr_query_builder: Dict[
    TimeSeriesAggregationOptionsType,
    Callable[[TimeSeriesOptions, Table], Tuple[Select, Column]],
] = {
    TimeSeriesAggregationOptionsType.MEAN: get_mean_select,
    TimeSeriesAggregationOptionsType.MOVING_AVG: get_moving_avg_select,
    TimeSeriesAggregationOptionsType.SUM: get_sum_select,
    TimeSeriesAggregationOptionsType.MIN: get_min_select,
    TimeSeriesAggregationOptionsType.MAX: get_max_select,
    TimeSeriesAggregationOptionsType.PERCENTILE: get_percentile_select,
    None: get_no_aggr_select,
}


def is_percentile_aggregation(aggr_type: str) -> bool:
    """
    Returns True if the aggregation type is a percentile
    """

    return aggr_type is not None and re.match(r"^[a-z]+-\d+$", aggr_type)


def get_base_select(
    options: TimeSeriesOptions, entity_data_table: Table
) -> Tuple[Select, Column]:
    """
    Returns the base select for the query:
        If no aggregation: select all value fields,
        If aggregation: select only float value field and apply aggregation
    The time column is labeled as "ts" in both cases
    """

    query = select(
        entity_data_table.c.entity_id,
        entity_data_table.c.attr_id,
    )

    aggr_type = options.aggregation.type if options.aggregation else None
    if is_percentile_aggregation(aggr_type):
        aggr_type = TimeSeriesAggregationOptionsType.PERCENTILE

    query, ts_column = __aggr_query_builder[aggr_type](
        query, options, entity_data_table
    )

    return query, ts_column
