from functools import reduce
from typing import List
from app.core.time_series import aggregations
import app.core.time_series.data_sources.quantum_leap.quantum_leam_constants as ql_constants
import app.core.time_series.data_sources.quantum_leap.models.utils as model_utils
from aether_pylib.time_series.time_series import TimeSeries, TimeSeriesValue
from aether_pylib.time_series.time_scope import TimeScope
from aether_pylib.time_series.time_series_options import (
    TimeSeriesOptions,
    TimeSeriesOrdering,
    WhereClause,
    WhereClauseOperation,
)
from aether_pylib.time_series.time_series_request import TimeSeriesRequest
from sqlalchemy.orm import Session, Query
from sqlalchemy import Table, Column, or_, and_, cast, Time
from sqlalchemy.sql import extract, func
from app.core.config.logging import appLogging as logging


def build_query(
    entity_urn: str,
    attrs: List[str],
    options: TimeSeriesOptions,
    table_model: Table,
    table_metadata: dict,
    db: Session,
) -> Query:
    """
    Build a time series request for a single entity, to the given table model
    Table metadata is used to get the actual column names for each attribute.
    If a table does not have an attribute, it will wont be returned, but
    no error will be raised (as this is the behavior of the api).
    """

    id_attr_column = model_utils.get_table_attr_column(
        table_model=table_model,
        table_metadata=table_metadata,
        attr=ql_constants.ID_ATTR,
    )

    # WARGING: always use is None, because the column has
    # the comparators overloaded for query building
    if id_attr_column is None:
        raise ValueError(f"ID column not found in table {table_model.name}")

    ts_attr_column = model_utils.get_table_attr_column(
        table_model=table_model,
        table_metadata=table_metadata,
        attr=ql_constants.TIME_ATTR,
    )

    if ts_attr_column is None:
        raise ValueError(f"Time column not found in table {table_model.name}")

    scope_attr = getattr(table_model.c, ql_constants.SCOPE_COLUMN, None)
    if scope_attr is None:
        raise ValueError(f"Scope column not found in table {table_model.name}")

    # base query with id, timestamp, and the requested attributes
    query = build_base_query(
        id_attr=id_attr_column,
        ts_attr=ts_attr_column,
        scope_attr=scope_attr,
        query_scope=options.scope,
        query_attrs=attrs,
        table_model=table_model,
        table_metadata=table_metadata,
        db=db,
    )

    if options.order == TimeSeriesOrdering.ASC:
        query = query.order_by(ts_attr_column.asc())
    else:
        query = query.order_by(ts_attr_column.desc())

    if entity_urn:
        # there might be a where clause, so no need to filter by id
        query = query.filter(id_attr_column == entity_urn)

    if options.start_date:
        query = query.filter(ts_attr_column >= options.start_date)

    if options.end_date:
        query = query.filter(ts_attr_column <= options.end_date)

    # where filter
    if options.where:
        query = apply_where_filter(query, options.where, table_metadata, table_model)

    # period filtering
    if options.period:
        for period in options.period:
            query = apply_period_filter(query, period, ts_attr_column)

    # limit
    if options.limit:
        query = query.limit(options.limit)

    return query


def build_base_query(
    id_attr: Column,
    ts_attr: Column,
    scope_attr: Column,
    query_scope: str,
    query_attrs: List[str],
    table_model: Table,
    table_metadata: dict,
    db: Session,
) -> Query:
    """
    Return a base query for the given table model, with the given attributes.
    The queried columns are: id, timestamp, and the attributes in query_attrs.
    The order is descending by timestamp.
    It is filtered by the given scope.
    """

    query = db.query(id_attr, ts_attr)

    for attr in query_attrs:
        attr_column = model_utils.get_table_attr_column(
            table_model=table_model,
            table_metadata=table_metadata,
            attr=attr,
        )

        if attr_column is None:
            logging.warning(f"Attribute {attr} not found in table {table_model.name}")
            continue

        query = query.add_columns(attr_column)

    # basic filter for the entity
    query = query.filter(scope_attr == query_scope)

    return query


def apply_period_filter(query: Query, period: TimeScope, ts_attr: Column) -> Query:
    """
    Apply the period filter to the query
    """

    basic_conditions = []

    # month filtering
    month_conditions = []
    if period.months:
        for month in period.months:
            month_conditions.append(extract("month", ts_attr) == month + 1)

    if month_conditions:
        basic_conditions.append(reduce(or_, month_conditions))

    # month day filtering
    month_day_conditions = []
    if period.month_days:
        for month_day in period.month_days:
            month_day_conditions.append(extract("day", ts_attr) == month_day + 1)

    if month_day_conditions:
        basic_conditions.append(reduce(or_, month_day_conditions))

    # week day filtering
    week_day_conditions = []
    if period.week_days:
        for week_day in period.week_days:
            week_day_conditions.append(extract("dow", ts_attr) == week_day + 1)

    if week_day_conditions:
        basic_conditions.append(reduce(or_, week_day_conditions))

    # hour filtering
    hour_conditions = []
    engine = query.session.get_bind()
    if period.hours:
        for hour in period.hours:
            if hour[0] <= hour[1]:
                hour_conditions.append(
                    func.time(ts_attr).between(func.time(hour[0]), func.time(hour[1]))
                    if engine.name == "sqlite"
                    # ON POSTGRES
                    else cast(ts_attr, Time).between(
                        cast(hour[0], Time), cast(hour[1], Time)
                    )
                )
            else:
                hour_conditions.append(
                    or_(
                        func.time(ts_attr) >= func.time(hour[0]),
                        func.time(ts_attr) <= func.time(hour[1]),
                    )
                    if engine.name == "sqlite"
                    # ON POSTGRES
                    else or_(
                        cast(ts_attr, Time) >= cast(hour[0], Time),
                        cast(ts_attr, Time) <= cast(hour[1], Time),
                    )
                )

    if hour_conditions:
        basic_conditions.append(reduce(or_, hour_conditions))

    filter_condition = reduce(and_, basic_conditions) if basic_conditions else None

    if period.extra:
        for extra in period.extra:
            extra_conditions = []
            if extra.year is not None:
                extra_conditions.append(extract("year", ts_attr) == extra.year)

            if extra.month is not None:
                extra_conditions.append(extract("month", ts_attr) == extra.month + 1)

            if extra.month_day is not None:
                extra_conditions.append(extract("day", ts_attr) == extra.month_day + 1)

            extra_condition = reduce(and_, extra_conditions)

            if extra.exclude:
                filter_condition = and_(filter_condition, ~extra_condition)
            else:
                filter_condition = or_(filter_condition, extra_condition)

    query = query.filter(filter_condition) if filter_condition is not None else query

    return query


def apply_where_filter(
    query: Query, where_clause: WhereClause, table_metadata: dict, table_model: Table
) -> Query:
    """
    Apply the where filter to the query
    """

    if where_clause.operation != WhereClauseOperation.AND:
        raise ValueError(
            f"Invalid operation: {where_clause.operation}. Only 'AND' is supported"
        )

    for condition in where_clause.conditions:
        query = apply_where_filter_condition(
            query=query,
            condition=condition,
            table_metadata=table_metadata,
            table_model=table_model,
        )

    return query


def apply_where_filter_condition(
    query: Query,
    condition: List[str | float | int | bool],
    table_metadata: dict,
    table_model: Table,
):
    """
    Apply a single where filter condition to the query
    For now, only equal operator is supported
    """

    if condition[1] != "=":
        raise ValueError(
            f"Invalid operator: {condition[1]}. Only equal operator is supported"
        )

    attr_column = model_utils.get_table_attr_column(
        table_model=table_model,
        table_metadata=table_metadata,
        attr=condition[0],
    )

    if attr_column is None:
        logging.warning(
            f"Attribute {condition[0]} not found in table {table_model.name}"
        )
        return query

    return query.filter(attr_column == condition[2])


def execute_query(
    query: Query, measure_ids: List[str], table_metadata: dict
) -> List[TimeSeries]:
    """
    Execute the query and return the results in a list of TimeSeries
    """

    def get_attr_index(attr: str) -> int:
        """
        Get the index of the attribute in the query results
        """
        attr_col_name = model_utils.get_attr_column(
            table_metadata=table_metadata, ngsi_attr=attr
        )

        if attr_col_name is None:
            return None

        return next(
            i
            for i, x in enumerate(query.column_descriptions)
            if x["name"] == attr_col_name
        )

    results = query.all()

    id_index = get_attr_index(ql_constants.ID_ATTR)

    if id_index is None:
        logging.error(
            f"Entity id column {ql_constants.ID_ATTR} not found in the query results"
        )
        return []

    ts_index = get_attr_index(ql_constants.TIME_ATTR)
    if ts_index is None:
        logging.error(f"Timestamp column not found in the query results")
        return []

    attr_indexes = []
    for measure_id in measure_ids:
        attr_column = model_utils.get_attr_column(
            table_metadata=table_metadata, ngsi_attr=measure_id
        )
        if attr_column is None:
            continue

        index = next(
            i
            for i, x in enumerate(query.column_descriptions)
            if x["name"] == attr_column
        )
        if index is None:
            continue

        attr_indexes.append((measure_id, index))

    result_ts = {}
    for row in results:
        entity_id = row[id_index]
        ts = row[ts_index]
        for measure_id, index in attr_indexes:
            ts_key = (entity_id, measure_id)
            if ts_key not in result_ts:
                result_ts[ts_key] = TimeSeries(
                    device_id=entity_id,
                    measure_id=measure_id,
                    values=[],
                )

            attr_value = row[index]
            if attr_value is None:
                continue

            result_ts[ts_key].values.append(
                TimeSeriesValue(
                    timestamp=ts,
                    value=attr_value,
                )
            )

    return list(result_ts.values())
