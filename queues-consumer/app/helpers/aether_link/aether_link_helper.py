from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import List, Tuple, TYPE_CHECKING, Generator

import requests
from aether_pylib.context_broker.update_entities_request import AttributeType

from config.config import settings, storage
from config.logging import appLogging as logging

if TYPE_CHECKING:
    import pandas as pd


def get_entities_by_type(entity_types: List[str], tenant: str, scope: str) -> dict:
    """
    Returns all entities of the given type, obtained from
    the Aether Link.
    """

    try:
        response = requests.get(
            f"{settings.GENERAL.AETHER_LINK_URL}/api/v1/context-broker/entities",
            params={
                "types": ",".join(entity_types),
            },
            headers={
                "tenant": tenant,
                "scope": scope,
            },
            timeout=settings.DEFAULT_AETHER_LINK_REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        return response.json()

    except Exception as e:
        logging.error(e)
        return None


def get_entities_by_type_paginated(
    entity_types: List[str],
    tenant: str,
    scope: str,
    limit: int = 100,
    timeout: int = None,
) -> Generator[dict, None, None]:
    """
    Pagination from the Aether-Link /entities endpoint.
    """
    offset = 0
    timeout = timeout or settings.DEFAULT_AETHER_LINK_REQUEST_TIMEOUT

    while True:
        response = requests.get(
            f"{settings.GENERAL.AETHER_LINK_URL}/api/v1/context-broker/entities",
            params={
                "types": ",".join(entity_types),
                "limit": limit,
                "offset": offset,
            },
            headers={"tenant": tenant, "scope": scope},
            timeout=timeout,
        )
        response.raise_for_status()
        entities = response.json()

        if not entities:
            break

        yield from entities
        offset += limit

        if len(entities) < limit:
            logging.info(
                f"[Pagination] Last page reached for types={entity_types} "
                f"(received {len(entities)} < limit {limit}). Total fetched: {offset + len(entities)}"
            )
            break


def get_platform_type_subscriptions(tenant: str, scope: str) -> List[str]:
    """
    Returns all Platform type subscriptions
    """

    response = requests.get(
        f"{settings.GENERAL.AETHER_LINK_URL}/api/v1/context-broker/platformTypeSubscriptions",
        headers={
            "tenant": tenant,
            "scope": scope,
        },
        timeout=settings.DEFAULT_AETHER_LINK_REQUEST_TIMEOUT,
    )

    response.raise_for_status()
    return response.json()


def get_data_types(tenant: str, scope: str) -> List[str]:
    """
    Returns all data types
    """

    response = requests.get(
        f"{settings.GENERAL.AETHER_LINK_URL}/api/v1/context-broker/dataTypes",
        headers={
            "tenant": tenant,
            "scope": scope,
        },
        timeout=settings.DEFAULT_AETHER_LINK_REQUEST_TIMEOUT,
    )

    response.raise_for_status()
    return response.json()


def update_platform_type_subscriptions(
    subscribe_types: List[str], unsubscribe_types: List[str], tenant: str, scope: str
) -> None:
    """
    Updates the Platform type subscriptions
    """

    body = []

    for subscribe_type in subscribe_types:
        body.append(
            {
                "value": subscribe_type,
                "op": "add",
            }
        )

    for unsubscribe_type in unsubscribe_types:
        body.append(
            {
                "value": unsubscribe_type,
                "op": "remove",
            }
        )

    response = requests.patch(
        f"{settings.GENERAL.AETHER_LINK_URL}/api/v1/context-broker/platformTypeSubscriptions",
        json=body,
        headers={
            "tenant": tenant,
            "scope": scope,
        },
        timeout=settings.DEFAULT_AETHER_LINK_REQUEST_TIMEOUT,
    )

    response.raise_for_status()


def get_time_series(time_series_request: dict) -> dict:
    """
    Returns the time series obtained from the Aether Link.
    """
    try:
        response = requests.post(
            f"{settings.GENERAL.AETHER_LINK_URL}/api/v1/time-series",
            json=time_series_request,
            timeout=settings.TIMESERIES_REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        return response.json()

    except Exception as e:
        logging.error(e)
        return {"status": "error"}


def delete_time_series(delete_request: List[dict]) -> dict:
    """
    Deletes the time series obtained from the Aether Link.
    """

    try:
        response = requests.delete(
            f"{settings.GENERAL.AETHER_LINK_URL}/api/v1/time-series",
            json=delete_request,
            timeout=settings.TIMESERIES_REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        return response.json()

    except Exception as e:
        logging.error(e)
        return {"status": "error"}


def time_series_to_df(time_series_response: List[dict]) -> pd.DataFrame:
    """
    Convert timeseries response to dataframe.
    """
    import pandas as pd

    if not time_series_response:
        return pd.DataFrame()

    # Flatten all data into records first
    records = []
    for response in time_series_response:
        if not isinstance(response, dict) or "time_series" not in response:
            logging.warning(f"Invalid response format, skipping: {type(response)}")
            continue
        for serie in response["time_series"]:
            device_id = serie["device_id"]
            measure_id = serie["measure_id"]
            for value in serie["values"]:
                records.append(
                    {
                        "timeinstant": value["timestamp"],
                        "entityId": device_id,
                        "measure_id": measure_id,
                        "value": value["value"],
                    }
                )

    if not records:
        return pd.DataFrame()

    # Pivot to get measures as columns
    df = pd.DataFrame(records)
    return df.pivot_table(
        index=["timeinstant", "entityId"],
        columns="measure_id",
        values="value",
        aggfunc="first",
    ).reset_index()


def _download_and_load_cache_file(local_path, s3_path):
    import pandas as pd

    try:
        path = storage.download_file(local_path, s3_path)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            df = pd.read_csv(path)

            os.remove(path)
            return df
    except Exception:
        pass

    return None


def _get_hourly_filenames(start_date, end_date):
    current_hour = start_date.replace(minute=0, second=0, microsecond=0)
    while current_hour < end_date:
        next_hour = current_hour + timedelta(hours=1)
        filename = (
            f"{current_hour.strftime('%Y-%m-%dT%H_%M_%S')}_to_"
            f"{next_hour.strftime('%Y-%m-%dT%H_%M_%S')}.csv"
        )
        yield current_hour, next_hour, filename
        current_hour = next_hour


def _normalize_timeinstant_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize timeinstant column to consistent datetime format.
    """
    import pandas as pd

    if "timeinstant" not in df.columns:
        return df

    df["timeinstant"] = df["timeinstant"].astype(str)

    # Add microseconds to timestamps missing them
    mask = ~df["timeinstant"].str.contains(".", regex=False, na=False)
    df.loc[mask, "timeinstant"] = df.loc[mask, "timeinstant"] + ".000000"

    df["timeinstant"] = pd.to_datetime(
        df["timeinstant"], errors="coerce", format="mixed"
    )
    df = df.dropna(subset=["timeinstant"])

    return df


def _fetch_batch_from_cache(
    device_ids: List[str],
    start: datetime,
    end: datetime,
    s3_data_cache_path: str,
    tenant: str,
    scope: str,
) -> List[pd.DataFrame]:
    """
    Download cache files for a time batch and return list of DataFrames.
    """
    batch_dfs = []
    for _, _, filename in _get_hourly_filenames(start, end):
        for urn in device_ids:
            urn_split = urn.split(":")[-1]
            s3_path = f"{s3_data_cache_path}/{tenant}/{scope}/{urn_split}/{filename}"
            local_path = f"{urn_split}_{filename}"
            df = _download_and_load_cache_file(local_path, s3_path)
            if df is not None:
                batch_dfs.append(df)
    return batch_dfs


def get_time_series_from_data_cache(
    time_series_request: dict,
    s3_data_cache_path: str = "data_cache/crowd",
    batch_hours: int = 24,
) -> pd.DataFrame:
    """
    Retrieves and combines time series data from the S3 cache.
    """
    import pandas as pd

    all_cached_dfs = []
    all_measures = set()
    global_start_date = None
    global_end_date = None

    for time_series_request_single in time_series_request:
        options = time_series_request_single.get("options", {})

        measures = time_series_request_single.get("measure_ids", [])
        start_date = datetime.fromisoformat(options.get("start_date")).replace(
            tzinfo=None
        )
        end_date = datetime.fromisoformat(options.get("end_date")).replace(tzinfo=None)

        scope = options.get("scope", "/").replace("/", "_")
        tenant = options.get("tenant")
        device_ids = time_series_request_single.get("device_ids", [])

        all_measures.update(measures)
        global_start_date = (
            min(global_start_date, start_date) if global_start_date else start_date
        )
        global_end_date = (
            max(global_end_date, end_date) if global_end_date else end_date
        )

        current_start = start_date
        while current_start < end_date:
            current_end = min(current_start + timedelta(hours=batch_hours), end_date)

            batch_dfs = _fetch_batch_from_cache(
                device_ids,
                current_start,
                current_end,
                s3_data_cache_path,
                tenant,
                scope,
            )

            if batch_dfs:
                all_cached_dfs.append(pd.concat(batch_dfs, ignore_index=True))

            current_start = current_end

    if not all_cached_dfs:
        return pd.DataFrame()

    final_df = pd.concat(all_cached_dfs, ignore_index=True)
    final_df = _normalize_timeinstant_column(final_df)

    if "timeinstant" in final_df.columns and global_start_date and global_end_date:
        final_df = final_df[
            (final_df["timeinstant"] >= global_start_date)
            & (final_df["timeinstant"] <= global_end_date)
        ]
    final_df.rename(
        columns={
            "israndommac": "random",
            "entityid": "entityId",
            "visitorid": "visitorId",
            "visitortype": "visitorType",
            "detectiontype": "detectionType",
        },
        inplace=True,
    )

    columns_to_keep = ["timeinstant", "entityId"] + list(all_measures)
    return final_df[[col for col in columns_to_keep if col in final_df.columns]]


def get_time_series_in_df_format(
    time_series_request: dict,
    get_from_cache: bool = True,
    df_live_row_processing_lambda=None,
    skip_aether=False,
    drop_nan=True,
) -> pd.DataFrame:
    """
    Returns the time series obtained from the Aether Link as a DataFrame.
    """
    import pandas as pd

    if not skip_aether:
        time_series_response = get_time_series(time_series_request)

        df_live = time_series_to_df(time_series_response)

        if df_live_row_processing_lambda:
            df_live = df_live_row_processing_lambda(df_live)
    else:
        df_live = pd.DataFrame()

    df_cache = pd.DataFrame()
    if get_from_cache:
        df_cache = get_time_series_from_data_cache(time_series_request)

    # Combine cached and live data
    df = pd.concat([df_cache, df_live], ignore_index=True)

    # Drop duplicates in case of overlap between cache and live data
    if not df.empty:
        df = df.drop_duplicates()

    if drop_nan:
        # Drop rows with NaN values
        df = df.dropna()

    return df


def get_iota_services(
    tenant: str, scope: str, entity_type: str, device_type_code: str = None
) -> dict:
    """
    Returns the iota services obtained from the Aether Link,
    if something fails, it raises an exception.
    """
    url = f"{settings.GENERAL.AETHER_LINK_URL}/api/v1/iota/services"
    params = {"entity_type": entity_type, "device_type_code": device_type_code}
    headers = {"tenant": tenant, "scope": scope}

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=settings.DEFAULT_AETHER_LINK_REQUEST_TIMEOUT,
    )

    response.raise_for_status()
    result = response.json()
    return result


def to_ngsi_null_if_null(value):
    if value is None:
        return {"@type": "@json", "@value": None}
    return value


def update_on_context_broker(
    urn: str, tenant: str, scope: str, attributes: List[AttributeType]
) -> dict:
    if not attributes:
        return {"updated": True, "response": "No attributes to update", "status": 200}

    request_entity_body_to_aether = {"id": urn, "attributes": {}}

    for attr_name, attr_content in attributes.items():
        attr_value = attr_content.get("value")
        attr_type = attr_content.get("type")
        if not attr_type:
            continue
        request_entity_body_to_aether["attributes"][attr_name] = {
            "type": attr_type,
            "value": to_ngsi_null_if_null(attr_value),
        }

    request_body_to_aether = {"entities": [request_entity_body_to_aether]}

    context_link_url = (
        f"{settings.GENERAL.AETHER_LINK_URL}/api/v1/context-broker/entities/update"
    )
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "tenant": tenant,
        "scope": scope,
    }

    try:
        response = requests.post(
            context_link_url,
            json=request_body_to_aether,
            headers=headers,
            timeout=settings.DEFAULT_AETHER_LINK_REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        response_body = response.json()
        errors = response_body.get("errors", [])
        updated = not errors

        return {
            "updated": updated,
            "response": response_body,
            "status": response.status_code,
        }
    except Exception as e:
        logging.error(e)
        return {"updated": False, "response": str(e), "status": 500}


def get_datamodel_apikey_resource(
    tenant: str, scope: str, datamodel: str
) -> Tuple[str, str]:
    """
    As it says, just get the apikey for a data model from a given tenant and scope,
    using the Aether Link.
    returns a tuple (apikey, resource)
    """

    services = get_iota_services(tenant, scope, datamodel)

    if not services or len(services) == 0:
        raise RuntimeError(
            f"Error getting service for params tenant: {tenant}, scope: {scope}, datamodel: {datamodel}"
        )

    if len(services) > 1:
        logging.warning(
            "More than one iota service found for params tenant: "
            + str(tenant)
            + ", scope: "
            + str(scope)
            + ", datamodel: "
            + str(datamodel)
        )

    service = services[0]
    apikey = service.get("apikey")
    resource = service.get("resource")

    if not apikey:
        raise RuntimeError(
            f"Error getting apikey for params tenant: {tenant}, scope: {scope}, datamodel: {datamodel}"
        )

    if not resource:
        raise RuntimeError(
            f"Error getting resource for params tenant: {tenant}, scope: {scope}, datamodel: {datamodel}"
        )

    return apikey, resource


def create_context_broker_entity(tenant: str, scope: str, entities: List[dict]) -> bool:
    """
    Creates entities in the Context Broker through Aether Link.

    Args:
        tenant: Tenant name
        scope: Scope name
        entities: List of entity objects to create

    Returns:
        bool: True if successful, False otherwise

    Raises:
        Exception: If the request fails
    """
    url = f"{settings.GENERAL.AETHER_LINK_URL}/api/v1/context-broker/entities/create"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "tenant": tenant,
        "scope": scope,
    }

    payload = {"entities": entities}

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=settings.DEFAULT_AETHER_LINK_REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        if response.status_code < 200 or response.status_code >= 300:
            logging.error(f"Failed to create entity in Context Broker: {response.text}")
            return False

        return True

    except Exception as e:
        logging.error(f"Error creating entity in Context Broker: {e}", exc_info=True)
        raise
