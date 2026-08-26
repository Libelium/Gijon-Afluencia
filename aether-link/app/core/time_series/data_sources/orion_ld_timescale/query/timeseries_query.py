from typing import List
from aether_pylib.time_series.time_series import TimeSeries, TimeSeriesValue
from aether_pylib.time_series.time_series_options import (
    TimeSeriesOptions,
    TimeSeriesOrdering,
)
from typing import List
from sqlalchemy.orm import Session, Query
from sqlalchemy import select, literal_column
from sqlalchemy.sql import func, over
from app.core.time_series.data_sources.orion_ld_timescale.orion_ld_timescale_constants import ATTRIBUTE_PREFIX
from app.core.time_series.data_sources.orion_ld_timescale.models.attribute import Attribute

def build_query(
    entity_urns: List[int],  # Updated to int as entityid is Integer
    attrs: List[str],
    options: TimeSeriesOptions,
    db: Session,
) -> Query:
    """
    Build a time series request for a single entity, to the given table model
    Table metadata is used to get the actual column names for each attribute.
    If a table does not have an attribute, it will not be returned, but
    no error will be raised (as this is the behavior of the api).
    """
    # Define columns for the subquery
    columns = [
        Attribute.id,
        Attribute.valuetype,
        Attribute.entityid,
        Attribute.text,
        Attribute.boolean,
        Attribute.number,
        Attribute.compound,
        Attribute.ts,
        # Window function for row numbering
        over(
            func.row_number(),
            partition_by=[Attribute.entityid, Attribute.id],
            order_by=Attribute.ts.desc() if options.order == TimeSeriesOrdering.DESC else Attribute.ts.asc()
        ).label("r")
    ]
    
    parsed_attrs = [f"{ATTRIBUTE_PREFIX}{attr}" for attr in attrs]

    # Construct the subquery with filtering and ordering
    subquery = (
        select(*columns)  # Unpack columns list here
        .where(
            Attribute.entityid.in_(entity_urns),
            Attribute.id.in_(parsed_attrs),
            Attribute.ts >= options.start_date if options.start_date else literal_column("TRUE"),
            Attribute.ts < options.end_date if options.end_date else literal_column("TRUE")
        )
        .order_by(
            Attribute.ts.desc() if options.order == TimeSeriesOrdering.DESC else Attribute.ts.asc(),
            Attribute.entityid.asc(),
            Attribute.id.asc()
        )
        .alias("registries")
    )

    # Outer query to apply row limit on the windowed row number
    query = db.query(subquery).filter(subquery.c.r <= options.limit) if options.limit else db.query(subquery)

    return query

def __get_attr_value(attr: Attribute):
    if attr.number is not None:
        return attr.number
    elif attr.text is not None:
        return attr.text
    elif attr.boolean is not None:
        return attr.boolean
    elif attr.compound is not None:
        return attr.compound
    else:
        return None


def __process_result_for_entity_attr(results: List[Attribute], entity_urn: str, attr: str) -> TimeSeries:
    entity_attr_attrs = [r for r in results if r.entityid == entity_urn and r.id == f"{ATTRIBUTE_PREFIX}{attr}"]
        
    return TimeSeries(
        device_id=entity_urn,
        measure_id=attr,
        values=[
            TimeSeriesValue(
                timestamp=attr.ts,
                value=__get_attr_value(attr)
            ) for attr in entity_attr_attrs if __get_attr_value(attr) is not None
        ]
    )
        

def execute_query(
    query: Query,
    entity_urns: List[str],
    attrs: List[str],
    db: Session
) -> List[TimeSeries]:
    """
    Execute the query and return the results in a list of TimeSeries
    """

    results = query.all()

    timeseries = []
    for entity_urn in entity_urns:
        for attr in attrs:
            timeseries.append(__process_result_for_entity_attr(results, entity_urn, attr))

    return timeseries
