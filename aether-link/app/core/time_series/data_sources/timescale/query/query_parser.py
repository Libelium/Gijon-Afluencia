from typing import Dict, List
from aether_pylib.time_series.time_series import TimeSeries, TimeSeriesValue
from sqlalchemy import Tuple
from app.core.config.logging import appLogging as logging
import dateutil.parser


def to_timeseries_schema(
    query_result: List[Tuple], attr_idx: Dict[str, int]
) -> List[TimeSeries]:
    """
    Transforms the query result into a list of TimeSeries objects,
    using the attr_idx dictionary to get the attribute index in the query result
    Args:
        query_result: The query result
        attr_idx: A dictionary with the attribute index in the query result
            e.g. {"ts": 1, "attr_value_type": 3}
    Returns:
        A list of TimeSeries objects
    """

    device_measure_dict: Dict[Tuple[str, str], List[TimeSeriesValue]] = {}

    entity_id_idx = attr_idx.get("entity_id")
    attr_id_idx = attr_idx.get("attr_id")
    attr_double_value_idx = attr_idx.get("attr_double_value")
    ts_idx = attr_idx.get("ts")

    # If no aggregation is needed, then we have to infer the type
    attr_value_type_idx = attr_idx.get("attr_value_type", None)
    attr_string_value_idx = attr_idx.get("attr_string_value", None)
    attr_boolean_value_idx = attr_idx.get("attr_boolean_value", None)
    attr_json_value_idx = attr_idx.get("attr_json_value", None)
    type_key_idx = {
        "double": attr_double_value_idx,
        "string": attr_string_value_idx,
        "boolean": attr_boolean_value_idx,
        "json": attr_json_value_idx,
    }

    for row in query_result:
        entity_id = row[entity_id_idx]
        attr_id = row[attr_id_idx]

        if (entity_id, attr_id) not in device_measure_dict:
            device_measure_dict[(entity_id, attr_id)] = []

        if attr_value_type_idx is not None:
            value_type = row[attr_value_type_idx]
            value = row[type_key_idx.get(value_type, attr_json_value_idx)]
        else:
            value = row[attr_double_value_idx]

        if value is None:
            logging.warning(
                f"Found a None value for entity_id: {entity_id}, attr_id: {attr_id}, will skip it"
            )
            continue

        formated_date = dateutil.parser.parse(row[ts_idx].isoformat(), ignoretz=True)

        device_measure_dict[(entity_id, attr_id)].append(
            TimeSeriesValue(timestamp=formated_date, value=value)
        )

    return [
        TimeSeries(
            device_id=device_id,
            measure_id=measure_id,
            values=values,
        )
        for (device_id, measure_id), values in device_measure_dict.items()
    ]
