"""
Hourly precipitation/temperature via Open-Meteo (free, no API key) - two
endpoints depending on whether the date is PAST or FUTURE:
  - Historical Weather API (archive-api.open-meteo.com): real history, any
    past date.
  - Forecast API (api.open-meteo.com): real forecast, up to ~16 days ahead
    (forecast_days, Open-Meteo's free ceiling) - beyond that there is no real
    forecast to ask for, only a default to fall back to (see weather_for()),
    the same decreasing-reliability-with-horizon problem the rest of this
    repo already has elsewhere, just for a feature that is not deterministic
    like holidays/high season.

Same pattern as helpers/model_storage.py: training_data.py NEVER calls the
network - it reads a small cache blob in storage, refreshed separately by
update_weather_cache() (meant for a daily cron, not for a request inside
training/prediction). With no cache yet, or no hour covered, precip_mm
defaults to 0.0 (assumes "no rain" rather than failing) and temp_c to None.

precip_mm is NEVER None once written to the cache (update_weather_cache
normalizes it - see there): the Historical API's own last few days often come
back with precipitation: null (ERA5 itself runs a few days behind "today"),
and a null that reached weather_for() unnormalized would surface as NaN two
layers up, tripping select_feature_columns/dropna in training_data.py.
"""
import json
import logging
import os
from datetime import date as date_cls, datetime, timedelta, timezone
from typing import Optional

import requests

from crowd_predictions.config import settings
from crowd_predictions.config.config import get_storage
from crowd_predictions.helpers.model_storage import segregated_key

logger = logging.getLogger(__name__)

# Slack over the training window so the cache always covers a bit more history than
# training can ask for; the pruning below is sized off the same total.
WEATHER_CACHE_MARGIN_DAYS = 35

HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

CACHE_FILENAME = "weather_cache.json"


def weather_cache_key() -> str:
    return segregated_key(settings.weather().WEATHER_CACHE_PREFIX, CACHE_FILENAME)


def _fetch_hourly(url: str, params: dict, lat: float, lon: float) -> list:
    """Calls Open-Meteo, returns [{"timestamp" (datetime), "precip_mm", "temp_c"}]."""
    query = {**params, "latitude": lat, "longitude": lon,
             "hourly": "precipitation,temperature_2m", "timezone": "UTC"}
    response = requests.get(url, params=query, timeout=30)
    response.raise_for_status()
    hourly = response.json()["hourly"]
    return [
        {"timestamp": datetime.fromisoformat(ts), "precip_mm": precip, "temp_c": temp}
        for ts, precip, temp in zip(hourly["time"], hourly["precipitation"], hourly["temperature_2m"])
    ]


def fetch_historical_weather(start_date: date_cls, end_date: date_cls, lat: float, lon: float) -> list:
    """Historical Weather API - PAST date range (inclusive)."""
    return _fetch_hourly(HISTORICAL_URL, {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }, lat, lon)


def fetch_forecast_weather(lat: float, lon: float, forecast_days: int = 16, past_days: int = 7) -> list:
    """
    Forecast API - next `forecast_days` days (16 = Open-Meteo's free ceiling) AND
    the last `past_days` (the API supports this natively). This is what closes the
    gap fetch_historical_weather leaves: the Historical Weather API (ERA5) is only
    asked up to yesterday, but ERA5 itself runs several days behind - the last few
    "past" days it claims to cover often come back with precipitation: null
    (see update_weather_cache). past_days=7 covers that lag with a real forecast
    value instead of leaving those hours uncovered.
    """
    return _fetch_hourly(FORECAST_URL, {"forecast_days": forecast_days, "past_days": past_days}, lat, lon)


def load_weather_cache(storage, local_dir: str = "/tmp") -> dict:
    """
    {timestamp_iso: {"precip_mm", "temp_c"}} - never raises. No cache uploaded
    yet (cold start, same contract as helpers/model_storage.load_model_bundle)
    or a download error both come back as an empty cache: every hour then
    falls to weather_for()'s default instead of failing training/prediction.
    """
    local_path = os.path.join(local_dir, CACHE_FILENAME)
    try:
        storage.download_file(weather_cache_key(), local_path)
        with open(local_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        # A truncated/corrupt blob (json.load) is as unusable as a download
        # failure - "never raises" has to cover both, not just the download.
        logger.warning(f"No usable weather cache in storage ('{weather_cache_key()}': {e})")
        return {}


def save_weather_cache(storage, cache: dict, local_dir: str = "/tmp") -> None:
    local_path = os.path.join(local_dir, CACHE_FILENAME)
    with open(local_path, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    storage.upload_file(weather_cache_key(), local_path)


def _coordinates_from_weather_targets(raw: str, tenant: str) -> Optional[tuple]:
    """
    (lat, lon) for `tenant` in WEATHER_TARGETS="tenant:lat:lon,tenant2:lat2:lon2",
    or None if it has no entry there.

    Only THIS tenant's entry is parsed, so a malformed one raises only for the
    tenant it belongs to - same "fail loud on garbage" as
    events_registry.append_event, but confined to who it concerns. Parsing the
    whole string would make a typo in one city's coordinates abort the OTHER
    tenants too: this is reached from train_pipeline._metrics() on every run,
    outside daily_pipeline's refresh try/except, so the blast radius is a failed
    training, not a skipped refresh.
    """
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = [part.strip() for part in chunk.split(":")]
        if parts[0] != tenant:
            continue
        if len(parts) != 3:
            raise ValueError(f"Malformed WEATHER_TARGETS entry {chunk!r} - expected tenant:lat:lon")
        try:
            return (float(parts[1]), float(parts[2]))
        except ValueError:
            raise ValueError(f"Malformed WEATHER_TARGETS entry {chunk!r} - lat/lon must be numbers")
    return None


def coordinates_for_current_tenant() -> Optional[tuple]:
    """
    (lat, lon) for the ACTIVE FIWARE_TENANT (os.environ, set by fiware_target()
    while a target is running - update_weather_cache() always runs inside one,
    see daily_pipeline.py/scripts/update_weather.py). Every tenant is a different
    city, so this is what WEATHER_LAT/WEATHER_LON alone cannot express in a
    multi-tenant deployment - applying one city's coordinates to every tenant is
    wrong in a way that looks correct (see the review that flagged this).

    Falls back to WEATHER_LAT/WEATHER_LON when WEATHER_TARGETS is unset, same
    fallback fiware_targets.parse_target_specs() uses for FIWARE_TARGETS itself, so an
    existing single-tenant deployment needs no change.

    None means "not configured for this tenant" (whether because WEATHER_TARGETS
    has no entry for it, or because nothing is configured at all) - a normal
    state, not an error; update_weather_cache() no-ops in that case.
    """
    weather_settings = settings.weather()
    raw = weather_settings.WEATHER_TARGETS
    if not raw.strip():
        return weather_settings.coordinates()

    tenant = settings.fiware().FIWARE_TENANT
    coordinates = _coordinates_from_weather_targets(raw, tenant)
    if coordinates is None:
        logger.warning(f"No WEATHER_TARGETS entry for tenant '{tenant}' - "
                       f"its weather cache stays untouched")
    return coordinates


def is_available_for_current_tenant() -> bool:
    """
    Whether precip_mm is backed by real coordinates for the active tenant, or
    still the constant 0.0 default everywhere. See
    warm_start.weather_availability_changed(): the day this flips true, precip_mm
    stops being a constant and a warm start would add trees on top of a booster
    that learned "it never rains" - same class of silent drift as
    CALENDAR_TIMEZONE changing, just for a different feature.
    """
    return coordinates_for_current_tenant() is not None


def update_weather_cache(storage=None, forecast_days: int = 16,
                          historical_days_back: int = None, local_dir: str = "/tmp") -> dict:
    """
    Refreshes the cache in storage: history of the last `historical_days_back`
    days + forecast of the next `forecast_days`. Meant to be called separately
    (a daily cron) - NEVER from training_data.py, a training/prediction run
    should not depend on network availability at that moment nor on "today"
    (breaks reproducibility).

    No-op (returns the existing cache unchanged) if there are no coordinates for
    the current tenant - see coordinates_for_current_tenant, this is meant to run
    safely even where nobody has configured weather yet.
    """
    # Derived, not a literal: the pruning below uses the same number, so a cache
    # shorter than the training window would silently drop the history it needs.
    # Imported here because aether_history reaches training_data, which reaches back.
    if historical_days_back is None:
        from crowd_predictions.helpers.aether_history import COLD_START_DAYS
        historical_days_back = COLD_START_DAYS + WEATHER_CACHE_MARGIN_DAYS
    storage = storage or get_storage()
    cache = load_weather_cache(storage, local_dir=local_dir)

    coordinates = coordinates_for_current_tenant()
    if coordinates is None:
        logger.warning("No weather coordinates for this tenant - leaving the weather cache untouched")
        return cache
    lat, lon = coordinates

    today = date_cls.today()
    historical = fetch_historical_weather(today - timedelta(days=historical_days_back), today - timedelta(days=1), lat, lon)
    forecast = fetch_forecast_weather(lat, lon, forecast_days)

    # historical first, forecast second - forecast's past_days overlaps the last few
    # historical days on purpose (see fetch_forecast_weather), but only fills a hole
    # (missing key or a null ERA5 reading), it never overwrites a real measurement
    # with a forecast guess for a day ERA5 already published cleanly.
    for point in historical:
        cache[point["timestamp"].isoformat()] = {"precip_mm": point["precip_mm"], "temp_c": point["temp_c"]}
    for point in forecast:
        key = point["timestamp"].isoformat()
        if key not in cache or cache[key]["precip_mm"] is None:
            cache[key] = {"precip_mm": point["precip_mm"], "temp_c": point["temp_c"]}

    # Last resort: Open-Meteo returning null for BOTH sources on the same hour
    # would be unusual, but "no rain" is a safer default than an unresolved gap
    # silently becoming NaN two layers up (see training_data.py/train_pipeline.py).
    for point in cache.values():
        if point["precip_mm"] is None:
            point["precip_mm"] = 0.0

    # Prune to the SAME window just fetched - without this the cache never
    # shrinks (timestamps are unique keys, so re-fetching the same days never
    # duplicates them either, but two years of daily runs still leave ~17500
    # hours that get downloaded WHOLE by every single train/predict run to read
    # the days training actually uses). historical_days_back is derived from
    # COLD_START_DAYS with margin, so nothing training can reach is ever pruned -
    # only what it could not use anyway.
    cutoff = today - timedelta(days=historical_days_back)
    pruned = {k: v for k, v in cache.items() if date_cls.fromisoformat(k[:10]) >= cutoff}
    dropped = len(cache) - len(pruned)
    if dropped:
        logger.info(f"Weather cache pruned: {dropped} hours older than {historical_days_back} days dropped")
    cache = pruned

    save_weather_cache(storage, cache, local_dir=local_dir)
    return cache


def refresh_weather_one_target(tenant: str, scope: str) -> int:
    """
    One target's worth of update_weather_cache(), for scripts/update_weather.py
    (a manual multi-target backfill) via run_for_each_target - tenant/scope are
    unused here directly (fiware_target() already pinned them in os.environ
    before this runs), but run_for_each_target calls every target function with
    the same (tenant, scope) signature.
    """
    cache = update_weather_cache()
    logger.info(f"weather cache refreshed - {len(cache)} hours cached")
    return 0


def weather_for(timestamp, cache: dict) -> dict:
    """
    {"precip_mm", "temp_c"} for the hour of `timestamp`. No entry in the cache
    (hour not covered yet, beyond the forecast horizon, or WEATHER_LAT/LON not
    configured at all) -> precip_mm=0.0 (assumes "no rain" - a safe default,
    never blocks anything) and temp_c=None (there is no reasonable "0" for
    temperature, left explicit that it is missing instead of invented).

    The cache is keyed by NAIVE UTC (_fetch_hourly reads Open-Meteo with
    timezone=UTC and never attaches a tzinfo). A tz-aware `timestamp` would
    otherwise build a key with a "+HH:MM" suffix that matches nothing in the
    cache - silently falling to the 0.0 default for the WHOLE dataset instead
    of erroring, exactly the kind of gap this file has been fixing elsewhere.
    Converted to real UTC first (not just stripped), so a non-UTC tz-aware
    timestamp still lands on the right hour.
    """
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    hour_key = timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
    point = cache.get(hour_key)
    if point is None:
        return {"precip_mm": 0.0, "temp_c": None}
    return dict(point)  # a copy - the caller mutating this must not corrupt the shared cache
