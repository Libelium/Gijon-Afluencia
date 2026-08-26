"""
Aether Link client: reads the sensor history from the platform (Context Broker +
time-series DB). Ported from the reference prediction ETL, kept generic on purpose -
anything crowd-specific lives in helpers/aether_history.py.

Reuses FIWARE_TENANT / FIWARE_SCOPE instead of adding the AETHER_* pair of the
reference repo: two independent pairs would let a deployment read the history from
one scope and write predictions into another, silently.

The environment is read on every call, not at import time, so tests can patch it.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

from crowd_predictions.config import settings

logger = logging.getLogger(__name__)

# Its own (much larger) timeout: a full-history request spans a year over several
# devices and the platform takes its time. It is not a hung request, it is a big
# one - a 10 s timeout here would just make cold-start training impossible.
TIMESERIES_REQUEST_TIMEOUT = 300


def aether_url() -> str:
    return settings.aether().AETHER_LINK_URL


def aether_tenant() -> str:
    return settings.fiware().FIWARE_TENANT


def aether_scope() -> str:
    return settings.fiware().FIWARE_SCOPE


def request_timeout() -> int:
    return settings.aether().AETHER_REQUEST_TIMEOUT


def timeseries_limit() -> int:
    return settings.aether().AETHER_TIMESERIES_LIMIT


class AetherConfigError(RuntimeError):
    """Aether is not configured (missing URL/tenant/scope).

    Its own exception type so the entry points can turn it into a single clear
    line ("AETHER_LINK_URL is missing") instead of an ugly traceback, and so it
    is never confused with "configured fine but the platform returned nothing".
    """


def validate_aether_config() -> Tuple[bool, str]:
    """(ok, error_message). Returns instead of raising because the reference repo
    calls it the same way from every function; raise_for_aether_config() is the
    raising wrapper the entry points use."""
    if not aether_url():
        return False, ("AETHER_LINK_URL is not configured (.env). Set it to the "
                       "Aether Link URL of the target environment.")
    if not aether_tenant():
        return False, "FIWARE_TENANT is not configured (.env)"
    if not aether_scope():
        return False, "FIWARE_SCOPE is not configured (.env)"
    return True, ""


def raise_for_aether_config() -> None:
    """Raises AetherConfigError with the specific missing variable."""
    is_valid, error_msg = validate_aether_config()
    if not is_valid:
        raise AetherConfigError(error_msg)


def parse_relative_date(date_spec: str) -> str:
    """
    Normalizes a UTC date into the ISO format the API expects
    ("YYYY-MM-DDTHH:MM:SS.000Z"). Accepts ISO with or without the Z, with a space
    instead of the T, and date-only. Raises ValueError on anything else.

    No relative specs ("-7d") despite the name, inherited from the reference repo.
    """
    date_spec = date_spec.strip()

    if "T" in date_spec and date_spec.endswith("Z"):
        return date_spec

    try:
        if "T" in date_spec:
            parsed = datetime.fromisoformat(date_spec.replace("Z", ""))
            return parsed.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        if " " in date_spec:
            parsed = datetime.strptime(date_spec, "%Y-%m-%d %H:%M:%S")
            return parsed.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        if len(date_spec) == 10 and "-" in date_spec:
            parsed = datetime.strptime(date_spec, "%Y-%m-%d")
            return parsed.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except ValueError as e:
        raise ValueError(
            f"Invalid date format: '{date_spec}'. Expected "
            f"'YYYY-MM-DDTHH:MM:SS.000Z' or 'YYYY-MM-DD HH:MM:SS' (UTC). Error: {e}"
        )

    raise ValueError(
        f"Invalid date format: '{date_spec}'. Expected "
        f"'YYYY-MM-DDTHH:MM:SS.000Z' or 'YYYY-MM-DD HH:MM:SS' (UTC)"
    )


def get_time_series(device_ids: List[str], measure_ids: List[str], start_date: str,
                    end_date: str, limit: Optional[int] = None) -> Optional[Dict]:
    """
    POST /api/v1/time-series -> first element of the response. None if the request
    failed; an empty "time_series" is a valid answer.

    Two traps: the body is a LIST of requests, not a single object, and the
    endpoint answers HTTP 307 so the redirect has to be followed (`requests` does
    it for POST 307; curl needs -L).
    """
    raise_for_aether_config()

    parsed_start_date = parse_relative_date(start_date)
    parsed_end_date = parse_relative_date(end_date)

    time_series_request = {
        "device_ids": device_ids,
        "measure_ids": measure_ids,
        "options": {
            "start_date": parsed_start_date,
            "end_date": parsed_end_date,
            "limit": limit or timeseries_limit(),
            "tenant": aether_tenant(),
            "scope": aether_scope(),
        },
    }

    url = f"{aether_url()}/api/v1/time-series"

    logger.info("Fetching time series from Aether...")
    logger.info(f"  Devices: {len(device_ids)}  Measures: {measure_ids}")
    logger.info(f"  Range: {parsed_start_date} to {parsed_end_date}")
    logger.info(f"  Tenant/scope: {aether_tenant()} / {aether_scope()}")

    try:
        # The list wrapper is the API contract, not a style choice - see docstring.
        response = requests.post(url, json=[time_series_request],
                                 timeout=TIMESERIES_REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        logger.error(f"Timeout reading time series from Aether (>{TIMESERIES_REQUEST_TIMEOUT}s)")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error reading time series: {e}")
        logger.error(f"Response: {e.response.text if e.response is not None else 'no response'}")
        return None
    except Exception as e:
        logger.error(f"Error reading time series from Aether: {e}")
        return None

    if isinstance(data, list):
        return data[0] if data else {}
    return data


def time_series_to_dataframe(time_series_response: Optional[Dict]) -> pd.DataFrame:
    """
    Flattens the response into a DataFrame [timestamp, device_id, measure_name,
    value], one row per measurement.

    An empty response is NOT an error: it returns an empty DataFrame and logs it.
    Whoever called has to decide whether "no data" is fatal (training) or merely
    a warning.
    """
    if not time_series_response:
        logger.warning("Empty response from Aether (no 'time_series')")
        return pd.DataFrame()

    time_series_list = time_series_response.get("time_series") or []
    if not time_series_list:
        logger.warning("Aether returned no series for the requested devices/measures")
        return pd.DataFrame()

    rows = []
    for series in time_series_list:
        if not isinstance(series, dict):
            continue

        device_id = series.get("device_id")
        measure_id = series.get("measure_id")
        if not device_id or not measure_id:
            continue

        for measurement in series.get("values") or []:
            if not isinstance(measurement, dict):
                continue
            # 'observedAt' as a fallback: the two names are used interchangeably
            # depending on which layer of the platform answers.
            timestamp = measurement.get("timestamp") or measurement.get("observedAt")
            value = measurement.get("value")
            if timestamp and value is not None:
                rows.append({"timestamp": timestamp, "device_id": device_id,
                             "measure_name": measure_id, "value": value})

    df = pd.DataFrame(rows)
    if df.empty:
        logger.warning("Aether returned series with no usable measurements")
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    logger.info(f"Time series read: {len(df):,} measurements")
    logger.info(f"  Period: {df['timestamp'].min()} - {df['timestamp'].max()}")
    logger.info(f"  Devices with data: {df['device_id'].nunique()}")
    return df


def get_time_series_as_dataframe(device_ids: List[str], measure_ids: List[str],
                                 start_date: str, end_date: str,
                                 limit: Optional[int] = None) -> pd.DataFrame:
    """get_time_series() + time_series_to_dataframe() in one call."""
    return time_series_to_dataframe(
        get_time_series(device_ids=device_ids, measure_ids=measure_ids,
                        start_date=start_date, end_date=end_date, limit=limit)
    )


def get_entities_by_type(entity_types: List[str], tenant: Optional[str] = None,
                         scope: Optional[str] = None) -> Optional[List[Dict]]:
    """
    GET /api/v1/context-broker/entities?types=... -> list of NGSI-LD entities.
    None on failure; an empty list means the query worked and found nothing.

    Here tenant/scope go as HEADERS, while the time-series endpoint takes them in
    the body's "options" (the platform's inconsistency, not ours).
    """
    raise_for_aether_config()

    url = f"{aether_url()}/api/v1/context-broker/entities"
    headers = {"tenant": tenant or aether_tenant(), "scope": scope or aether_scope()}
    # Orion-LD paginates by default to 20 entities and caps 'limit' at 1000
    # (above that it answers 400), so the pages have to be walked through.
    # Needs aether-link >= v0.7.9: older versions ignore limit/offset and the
    # loop silently degrades back to a single page of 20.
    PAGE_SIZE = 1000
    MAX_PAGES = 100  # 100k entities; on reaching it we warn, never cut in silence

    logger.info(f"Querying the broker for entities of type: {', '.join(entity_types)}")

    all_entities: List[Dict] = []
    offset = 0

    for page in range(MAX_PAGES):
        params = {"types": ",".join(entity_types),
                  "limit": PAGE_SIZE, "offset": offset}

        try:
            response = requests.get(url, params=params, headers=headers,
                                    timeout=request_timeout())
            response.raise_for_status()
            batch = response.json()
        except Exception as e:
            logger.error(f"Error querying entities in the broker: {e}")
            return None

        if not isinstance(batch, list):
            logger.error(f"Unexpected response from the broker (expected a list): {type(batch)}")
            return None

        if not batch:
            break

        all_entities.extend(batch)

        # A short page was the last one: no need for one more round trip.
        if len(batch) < PAGE_SIZE:
            break

        offset += PAGE_SIZE
    else:
        logger.error(f"MAX_PAGES ({MAX_PAGES}) reached for {entity_types}: the entity "
                     f"list may be INCOMPLETE ({len(all_entities)} entities so far)")

    logger.info(f"  {len(all_entities)} entities returned")
    return all_entities
