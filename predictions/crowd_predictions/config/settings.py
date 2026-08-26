"""
Every environment variable of the repo in one place, typed and validated by
pydantic-settings, grouped by domain (sensors, sessions, fusion, storage, FIWARE,
queue, Aether, calendar, training, prediction, weather, OTE ingestion, anomalies).

⚠️ The accessors at the bottom build a NEW instance on EVERY call and nothing here
is cached. helpers/fiware_targets.py isolates each target by temporarily mutating
os.environ, so a cached FIWARE_TENANT would make every target read the first one's
without any error. It is also what lets the tests patch.dict(os.environ).
"""

import json
import logging
import os
from typing import Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# .env goes into os.environ, which is the ONLY source these settings read. No
# env_file= on purpose: pydantic would then read .env from disk as a second source,
# and a test doing patch.dict(os.environ, clear=True) would still see the values of
# the developer's own .env.
load_dotenv()


class EnvSettings(BaseSettings):
    """Base of every block: reads os.environ at INSTANTIATION, never at import."""

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=True)

    @model_validator(mode="before")
    @classmethod
    def _empty_means_unset(cls, values):
        """`VAR=` in .env means "not set" all over .env.example. Dropping the key
        applies the field default; keeping "" would fail validation on the typed
        fields (int/float/bool)."""
        if isinstance(values, dict):
            return {k: v for k, v in values.items()
                    if not (isinstance(v, str) and not v.strip())}
        return values


# Defaults with a reason behind the number live here as named constants: they used
# to be a DEFAULT_* in whichever module happened to read the variable, and the
# module and the .env.example drifted apart. Importable, so a test asserts against
# the same value the code uses.


DEFAULT_ENTITY_TYPE = "CrowdFlowObserved"
# MEDIUM as the compromise: the widest window over-counts the most and the shortest
# is the noisiest at hourly cadence. It is also the only one carrying data in PRE.
DEFAULT_MEASURE_ID = "peopleCountMediumInterval"
# Days set aside to measure a cold start. train.py trims it to a third of the
# usable span when the history is too short to afford it.
DEFAULT_HOLDOUT_DAYS = 14
# Widens the warm start's READING window: (28 of lookback + these) days. NOT the days
# of rows trained on - it trains with every usable row of the window minus the last
# one, which is held out for the metric.
DEFAULT_INCREMENTAL_TRAIN_DAYS = 2
# Fraction of a rolling window's days that must exist for rolling_mean_*/std_* to
# return a value instead of NaN. A percentage and not "every day" because the
# gaps are legitimate: bins only exist where the sensor reported.
DEFAULT_ROLLING_MIN_COVERAGE = 0.75
# Trade-off with MAX_ESTIMATORS: the more per run, the sooner the
# cap forces a full retrain.
DEFAULT_N_ESTIMATORS_INCREMENT = 50
# SAFETY NET, not the schedule: FULL_RETRAIN_AFTER_DAYS is what normally triggers a
# full retrain, and this has to stay ABOVE it (30 days x 50 trees = 1500) or the cap
# would always fire first. It only bites in the anomalous case - a job running more
# often than daily, or a bigger increment. Trees are never removed, so without any
# cap the booster grows for ever, slower and more overfitted to the last few days.
DEFAULT_MAX_ESTIMATORS = 2000
# Hours of recursive backtest after a full retrain, to get a MAE PER horizon step.
# evaluate_model() only measures one step over real lag/rolling, so without this the
# `horizonStep` we publish is a qualitative warning with no number behind it. It costs
# one rebuild of the feature table per step, so it is bounded; 0 disables it.
DEFAULT_BACKTEST_HORIZON_HOURS = 24
# Rounds without improvement on the validation slice before xgboost stops adding
# trees. The slice is carved out of the TRAIN side, never out of the holdout: choosing
# the number of trees on the holdout would make the reported MAE optimistic. 0
# disables it and the model trains the full n_estimators, as it did before.
DEFAULT_EARLY_STOPPING_ROUNDS = 50
# How stale the FRESHEST bin may be before the target goes red. Separates the two
# reasons for "no new data": the cron ran twice within the hour (fine, green) from
# ingestion having died days ago (not fine - without this the job stays green for
# ever, because a full retrain over the same stale rows also succeeds).
DEFAULT_MAX_DATA_STALENESS_DAYS = 3
# Age of the last FULL retrain past which the next run does one, whatever the tree
# count. By age and not "day 1 of the month": a run missed on day 1 would skip a
# whole month, and with several targets it would stack every tenant's expensive
# retrain into the same run - by age each target keeps its own date and they spread
# out on their own.
DEFAULT_FULL_RETRAIN_AFTER_DAYS = 30
# Margin of the before/after comparison over the same held-out day: a slightly
# worse MAE is boosting noise, a clearly worse one means the increment hurt.
DEFAULT_MAE_TOLERANCE = 1.10
# Storage key prefix. The flat key it replaced let two deployments over the same
# bucket overwrite each other's model.
DEFAULT_MODELS_PREFIX = "prediction-models"
# The bins are stored in UTC, but hour/weekday/holiday are LOCAL-calendar concepts:
# at UTC+2, a Sunday 00:30 local is a Saturday 22:30 UTC and would be labelled
# Saturday - which is where the nightlife volume is. Used ONLY to derive the calendar
# features; storage and published timestamps stay UTC.
# CALENDAR_TIMEZONE and HOLIDAYS_COUNTRY have NO default: every hour belongs to some
# timezone and every deployment to some country, so there is no neutral value to fall
# back to - inheriting another deployment's shifts every calendar feature in silence.
# The `holidays` library is used rather than a list of dates because it computes the
# MOVABLE holidays (Easter week) by itself every year.
# Absent subdivision = national holidays only, and absent ranges = no high season.
# Both are neutral: they lose precision instead of marking the wrong days.
DEFAULT_HIGH_SEASON_RANGES = ""
# Entity type of the zone aggregate published by the fusion ETL. It exists in the
# platform (the backend models CrowdFlowZone), unlike the one below.
DEFAULT_CROWD_FLOW_ZONE_ENTITY_TYPE = "CrowdFlowZone"
# Local output directories. Here and not as literals in the ETLs so the transform's
# own default and the setting cannot drift apart.
DEFAULT_PREDICTIONS_OUTPUT_DIR = "predictions_per_zone"
DEFAULT_PREDICTIONS_FORECAST_OUTPUT_DIR = "predictions_forecast"
# PROVISIONAL: there is no official datamodel for crowd predictions in the platform yet.
# Renaming it later means renaming the entities already created.
DEFAULT_PREDICTION_ENTITY_TYPE = "CrowdFlowPrediction"

# --- anomaly_detection/ (see AnomalySettings) ---
# Root of the whole vertical in storage. Everything hangs off it, segregated by
# tenant/scope like every other key this repo writes (helpers/model_storage.
# segregated_key), so two deployments over one bucket cannot read each other:
#   anomalies_detection/{tenant}/{scope}/*.csv        to process
#   anomalies_detection/{tenant}/{scope}/models/      one bundle per datamodel
#   anomalies_detection/{tenant}/{scope}/processed/   scored, with isOutlier
DEFAULT_ANOMALY_PREFIX = "anomalies_detection"
# Cyclic calendar features, canonical order. "month" is what lets a signal with a
# yearly cycle (tourist season, irrigation) be learnt at all; with less than a year
# of history it is simply a feature the model has not seen vary yet, never an error.
ANOMALY_CALENDAR_CYCLES = ("hour", "weekday", "month")
# EMPTY on purpose: a datamodel gets the seasonality it actually has, declared. A
# cycle the signal does not have is 2 dimensions of pure noise diluting the distance.
DEFAULT_ANOMALY_CALENDAR = ()
# In TIME, not in points: the same 30 days are 720 samples hourly and 8640 at 5 min.
DEFAULT_ANOMALY_DECAY_DAYS = 30.0
# Minimum fraction of rows a column must be present in to become a measure. A point
# needs ALL its measures at the same instant, so a sparse column makes every row that
# lacks it unscorable. Per datamodel because how sparse an export is depends on the
# reporting cadence of whatever produced it.
DEFAULT_ANOMALY_MIN_MEASURE_COVERAGE = 0.9
# Span of the recent-volatility window (rolling std / delta).
DEFAULT_ANOMALY_ROLLING_HOURS = 5.0
# How long a sustained shift takes to be accepted as the new normal.
DEFAULT_ANOMALY_REGIME_SHIFT_HOURS = 3.0

# PROVISIONAL, same reason as DEFAULT_PREDICTION_ENTITY_TYPE: the datamodel
# documentation marks these names as not fixed in the platform yet. Published by an ETL
# outside this repo, one entity per zone per window - see helpers/lidar_zone_history.py.
DEFAULT_LIDAR_ZONE_ENTITY_TYPE = "CrowdFlowLidarZone"
# totalConcurrentMax, NEVER totalCount: aforo (simultaneous), not afluencia (cumulative) -
# see the aforo/afluencia note in lidar_estimation.py. Also provisional/configurable in case
# the attribute name changes before the entity type is fixed.
DEFAULT_LIDAR_ZONE_CONCURRENT_ATTR = "totalConcurrentMax"
# How old a CrowdFlowLidarZone reading may be before it stops counting as "this
# window". The broker serves the last value for ever, so without this a stopped
# upstream ETL keeps the fusion publishing a frozen occupancy as "measured".
#
# THREE HOURS, and the number is not arbitrary: that ETL runs HOURLY and stamps each
# sample with the START of its window, not with the publish instant. So the freshest
# possible reading is already up to 60 min old by observedAt, plus its own processing
# lag - anything at or below 60 here would discard every reading and blank the LIDAR
# side permanently. This leaves room for two missed windows before crying wolf.
# 0 disables the check.
DEFAULT_LIDAR_ZONE_MAX_AGE_MINUTES = 180.0
# Storage key prefix for the weather cache (see helpers/model_storage.segregated_key -
# same collision problem as the model key, a different file).
DEFAULT_WEATHER_CACHE_PREFIX = "weather-cache"
# Silence that closes a presence segment. Well above the 200 ms of the tracking layer:
# a person occluded for a few seconds must not become two visits.
DEFAULT_OTE_TRACK_GAP_SECONDS = 30
# Net displacement under which a track is COUNTED as stationary, never filtered out.
# Measured: two objects walked 14 and 37 m to end up 10 and 47 cm from the start.
DEFAULT_OTE_STATIONARY_MAX_DISPLACEMENT_M = 1.0
# Closed list of labels.type getting their own series, HIGHEST PRIORITY FIRST. The order
# is not cosmetic: when the SAME track was seen labelled as more than one of these inside
# one report window (see resolve_label() in etl/ote/transform.py), whichever is listed
# earliest here wins - never whichever the sensor reported first. A LIDAR only ever loses
# precision by occlusion (a car half inside the sensor's edge reads as something smaller
# and self-corrects as more of it comes into view, never the other way round), so vehicle
# outranks adult. Also still the reason the list is closed at all: the importation_job
# creates attributes from the CSV columns without validating, so an unexpected value would
# grow an attribute nobody decided.
DEFAULT_OTE_LABEL_ATTRS = "vehicle,adult"
# Aggregation window of the ingestion, and the cadence of the entry point.
DEFAULT_OTE_WINDOW_SECONDS = 3600
# Staging area of fiware-manager, emptied on every run:
# <prefix>/<device_id>/YYYY/MM/DD/<ms>-<pid>-<seq>.ndjson.gz
DEFAULT_OTE_INCOMING_PREFIX = "ote/incoming"
# The archive proper, written by the compaction and read by the ETL:
# <prefix>/<device_id>/YYYY/MM/DD/YYYYMMDD-HHMM-HHMM.ndjson.gz
DEFAULT_OTE_RAW_PREFIX = "ote/raw"
# Its OWN prefix and not next to the archived object: recover() lists every manifest on
# every run, and beside the data that means walking the whole history to find a handful.
DEFAULT_OTE_MANIFEST_PREFIX = "ote/manifests"
# Where the deployment's own zones.json lives (see zones_config.py). Under ote/
# because the zones ARE the LIDAR installation; segregated by tenant/scope inside.
DEFAULT_OTE_ZONES_PREFIX = "ote/zones"
# The file name timestamp is the START of the dump window, so reading from
# `from - margin` is what keeps the first minutes of every run from going missing.
DEFAULT_OTE_READ_MARGIN_SECONDS = 3600
# An archived object is filed under the day it STARTED, and covers everything staged in
# its run, so after an outage it starts before the window it still holds. Days to list
# before the window: raise it if the CronJob has been down longer than this.
DEFAULT_OTE_ARCHIVE_LOOKBACK_DAYS = 1
# Concurrent downloads per device while compacting. The work is waiting on the network,
# not computing, so this has nothing to do with the number of cores. The real ceiling is
# botocore's connection pool, 10 by default: above that the extra threads just queue for a
# connection. Raising it past 10 means also raising max_pool_connections in the client's
# Config - worth it only where the storage is on the same network (MinIO on-premise).
DEFAULT_OTE_DOWNLOAD_WORKERS = 8
# PROVISIONAL: no LIDAR datamodel is registered in the platform yet, and renaming these later
# renames the entities already created.
DEFAULT_OTE_ZONE_ENTITY_TYPE = "CrowdFlowLidarZone"
DEFAULT_OTE_DEVICE_ENTITY_TYPE = "CrowdFlowLidarDevice"
# The crowd metrics PER SENSOR, apart from the device's health. Its own type because the
# two answer different questions - "is the sensor alive" and "how many people did it see" -
# and because the sensors barely overlap (they are far enough apart), so the
# zone aggregate hides which of its several sensors carries the traffic.
DEFAULT_OTE_OBSERVED_ENTITY_TYPE = "CrowdFlowLidarObserved"


class SensorSettings(EnvSettings):
    """Sensor segregation, for on-premise deployments without LIDAR."""

    ENABLE_SMARTSPOT: bool = True
    ENABLE_LIDAR: bool = True


class FusionSettings(EnvSettings):
    """Input and output of the LIDAR+SmartSpot fusion ETL (main.py)."""

    # "real" by default: a ConfigMap that forgets this must not silently publish made-up
    # occupancy against a live tenant and train the model on it (see etl/crowd/extract.py).
    DATA_SOURCE: str = "real"
    SYNTHETIC_DAYS: int = 5
    PREDICTIONS_OUTPUT_DIR: str = DEFAULT_PREDICTIONS_OUTPUT_DIR
    CROWD_FLOW_ZONE_ENTITY_TYPE: str = DEFAULT_CROWD_FLOW_ZONE_ENTITY_TYPE
    # DATA_SOURCE=real: which entity/attribute helpers/lidar_zone_history.py reads for the
    # LIDAR side of the fusion. See the DEFAULT_ constants above for why these are settings
    # and not hardcoded.
    LIDAR_ZONE_ENTITY_TYPE: str = DEFAULT_LIDAR_ZONE_ENTITY_TYPE
    LIDAR_ZONE_CONCURRENT_ATTR: str = DEFAULT_LIDAR_ZONE_CONCURRENT_ATTR
    LIDAR_ZONE_MAX_AGE_MINUTES: float = DEFAULT_LIDAR_ZONE_MAX_AGE_MINUTES
    # Zones to read CrowdFlowZone history for (helpers/aether_history.resolve_zone_ids()).
    # Empty = autodiscovery in the broker, same convention as AetherSettings.DEVICE_IDS.
    ZONE_IDS: str = ""

    def zone_id_list(self) -> list:
        return [z.strip() for z in self.ZONE_IDS.split(",") if z.strip()]


class StorageSettings(EnvSettings):
    """Backend selection and the key prefix. The credentials of each backend live
    in config/s3_storage_settings.py and config/local_storage_settings.py."""

    STORAGE_TYPE: str = "s3"
    MODELS_PREFIX: str = DEFAULT_MODELS_PREFIX


class FiwareSettings(EnvSettings):
    """
    The tenant/scope pair, used for THREE things on purpose: the queue message, the
    model key in the bucket and the Aether queries. There is no separate
    AETHER_TENANT/AETHER_SCOPE - two independent pairs would let a deployment read
    the history from one scope and write the predictions into another, silently.
    """

    FIWARE_TENANT: str = ""
    FIWARE_SCOPE: str = "/"
    FIWARE_TARGETS: str = ""


class QueueSettings(EnvSettings):
    """The platform queue (carrot), the reliable publication path."""

    QUEUES_CONSUMER_API_URL: Optional[str] = None
    # Who the importation job is attributed to. NO default on purpose: the consumer
    # tracks the job AND sends a user notification per published CSV, so a wrong id
    # floods a real person with cron noise (the inherited 1 was the admin).
    QUEUES_CONSUMER_USER_ID: Optional[int] = None


class AetherSettings(EnvSettings):
    """Aether Link: reading the live history from the platform."""

    AETHER_LINK_URL: str = ""
    AETHER_REQUEST_TIMEOUT: int = 10
    AETHER_TIMESERIES_LIMIT: int = 200000
    ENTITY_TYPE: str = DEFAULT_ENTITY_TYPE
    CROWD_MEASURE_ID: str = DEFAULT_MEASURE_ID
    # Empty = autodiscovery in the broker.
    DEVICE_IDS: str = ""

    @field_validator("AETHER_LINK_URL")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        """Every caller concatenates paths onto it; a trailing slash would produce
        "//api/v1/..." which this platform does not redirect."""
        return value.rstrip("/")

    def device_id_list(self) -> list:
        return [d.strip() for d in self.DEVICE_IDS.split(",") if d.strip()]


class CalendarSettings(EnvSettings):
    """
    Where the calendar features come from. Per deployment: with the wrong region
    `is_holiday` does not fail, it just marks the wrong days - and the model learns
    that people go out on a Tuesday that was never a holiday there.
    """

    CALENDAR_TIMEZONE: Optional[str] = None
    HOLIDAYS_COUNTRY: Optional[str] = None
    # "none" = the whole country, with no regional holidays. Absent means the same;
    # the explicit word exists so a target can override an inherited value.
    HOLIDAYS_SUBDIVISION: Optional[str] = None

    @field_validator("CALENDAR_TIMEZONE")
    @classmethod
    def _must_be_a_real_timezone(cls, value):
        """A typo here would silently shift every calendar feature, so it fails at
        startup naming the variable instead."""
        if not value:
            return None
        try:
            ZoneInfo(value)
        except Exception:
            raise ValueError(f"CALENDAR_TIMEZONE: '{value}' is not a known IANA timezone "
                              "(e.g. Europe/Madrid, UTC)") from None
        return value

    def timezone(self) -> str:
        """Fails instead of guessing: see the comment on the constants above."""
        if not self.CALENDAR_TIMEZONE:
            raise ValueError(
                "CALENDAR_TIMEZONE is not set and there is no fallback: every calendar "
                "feature (hour, weekday, is_weekend, is_holiday) would be built in the "
                "wrong local time. Set it to the deployment's IANA timezone.")
        return self.CALENDAR_TIMEZONE

    def country(self) -> str:
        if not self.HOLIDAYS_COUNTRY:
            raise ValueError(
                "HOLIDAYS_COUNTRY is not set and there is no fallback: is_holiday would "
                "mark another country's holidays. Set it to the deployment's ISO code.")
        return self.HOLIDAYS_COUNTRY

    def describe(self) -> str:
        """One line for the startup log - what turns "the model predicts weird" into
        "it is using another province's calendar" without reading a ConfigMap."""
        return (f"calendar: tz={self.CALENDAR_TIMEZONE} country={self.HOLIDAYS_COUNTRY} "
                f"subdivision={self.HOLIDAYS_SUBDIVISION or 'none'} "
                f"high_season={self.HIGH_SEASON_RANGES or 'none'}")

    @field_validator("HOLIDAYS_SUBDIVISION")
    @classmethod
    def _none_means_whole_country(cls, value):
        return None if value and value.strip().lower() == "none" else value
    # "MM-DD..MM-DD" pairs, comma separated. A range may cross the year end.
    HIGH_SEASON_RANGES: str = DEFAULT_HIGH_SEASON_RANGES

    def high_season_ranges(self) -> list:
        """[((month, day), (month, day))]. Parsed here and not where it is used so a
        malformed value fails at startup naming the variable."""
        ranges = []
        for chunk in self.HIGH_SEASON_RANGES.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            start, separator, end = chunk.partition("..")
            if not separator:
                raise ValueError(f"HIGH_SEASON_RANGES: '{chunk}' is not 'MM-DD..MM-DD'")
            ranges.append((_month_day(start, chunk), _month_day(end, chunk)))
        return ranges


def _month_day(text: str, chunk: str) -> tuple:
    """'06-15' -> (6, 15), rejecting anything that is not a real month/day."""
    try:
        month, day = (int(part) for part in text.strip().split("-"))
    except ValueError:
        raise ValueError(f"HIGH_SEASON_RANGES: '{text}' in '{chunk}' is not MM-DD") from None
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        raise ValueError(f"HIGH_SEASON_RANGES: '{text}' in '{chunk}' is not a real month/day")
    return month, day


class EventSettings(EnvSettings):
    """
    Weight per event type for the `event_magnitude` feature. Configurable because the
    event types themselves are per deployment: adding one used to mean editing code
    and shipping an image. JSON object, e.g. EVENT_MAGNITUDES={"large_event": 2}.
    Merged over the built-in weights, so an empty value keeps today's behaviour.
    """

    EVENT_MAGNITUDES: str = ""

    def magnitudes(self) -> dict:
        """Invalid JSON is ignored with an error rather than taking training down:
        the fallback is the built-in table, which is always usable."""
        if not self.EVENT_MAGNITUDES:
            return {}
        try:
            parsed = json.loads(self.EVENT_MAGNITUDES)
        except json.JSONDecodeError as e:
            logger.error(f"EVENT_MAGNITUDES is not valid JSON, ignoring it entirely: {e}")
            return {}
        if not isinstance(parsed, dict):
            logger.error(f"EVENT_MAGNITUDES must be a JSON object keyed by event type, "
                         f"got {type(parsed).__name__} - ignoring it entirely.")
            return {}
        return {str(k): int(v) for k, v in parsed.items() if str(v).lstrip("-").isdigit()}


class TrainingSettings(EnvSettings):
    """train.py, including the warm start knobs."""

    MODEL_OUTPUT_PATH: str = "crowd_xgboost_model.json"
    TRAINING_HOLDOUT_DAYS: int = DEFAULT_HOLDOUT_DAYS
    # Empty = the floor computed by helpers/aether_history.minimum_window_hours().
    INCREMENTAL_HOURS: Optional[int] = None
    INCREMENTAL_TRAIN_DAYS: int = DEFAULT_INCREMENTAL_TRAIN_DAYS
    ROLLING_MIN_COVERAGE: float = DEFAULT_ROLLING_MIN_COVERAGE
    N_ESTIMATORS_INCREMENT: int = DEFAULT_N_ESTIMATORS_INCREMENT
    MAX_ESTIMATORS: int = DEFAULT_MAX_ESTIMATORS
    FULL_RETRAIN_AFTER_DAYS: int = DEFAULT_FULL_RETRAIN_AFTER_DAYS
    MAX_DATA_STALENESS_DAYS: int = DEFAULT_MAX_DATA_STALENESS_DAYS
    EARLY_STOPPING_ROUNDS: int = DEFAULT_EARLY_STOPPING_ROUNDS
    BACKTEST_HORIZON_HOURS: int = DEFAULT_BACKTEST_HORIZON_HOURS
    INCREMENTAL_MAE_TOLERANCE: float = DEFAULT_MAE_TOLERANCE
    FORCE_FULL_RETRAIN: bool = False


class PredictionSettings(EnvSettings):
    """predict.py."""

    MODEL_INPUT_PATH: str = "crowd_xgboost_model.json"
    PREDICTION_HORIZON_HOURS: int = 24
    # Empty = auto-computed right after the last real data point.
    PREDICTION_START: Optional[str] = None
    PREDICTIONS_FORECAST_OUTPUT_DIR: str = DEFAULT_PREDICTIONS_FORECAST_OUTPUT_DIR
    # PROVISIONAL, see the constant. Changing it renames the published entities.
    PREDICTION_ENTITY_TYPE: str = DEFAULT_PREDICTION_ENTITY_TYPE


class WeatherSettings(EnvSettings):
    """
    Open-Meteo (free, no API key). Rain reduces outdoor crowd counts, and this is
    the feature that carries it into the model - see training_data.py.

    LAT/LON have no default, unlike the rest of this file: every other default
    here is a reasonable behaviour, but there is no reasonable latitude/longitude
    to fall back to. Optional rather than required, though: `precip_mm` is a
    supplementary feature (0.0 with no cache, never breaks training - see
    training_data.py), and this settings block is read on EVERY calendar-feature
    call. A required field would turn "weather not configured yet" into "training
    does not run at all", for a feature meant to do no harm when absent.
    """

    WEATHER_LAT: Optional[float] = None
    WEATHER_LON: Optional[float] = None
    WEATHER_CACHE_PREFIX: str = DEFAULT_WEATHER_CACHE_PREFIX
    # Per-tenant coordinates: "tenant:lat:lon,tenant2:lat2:lon2" - every tenant is a
    # different city, so a single WEATHER_LAT/LON applies one city's rain to all of
    # them. Empty -> WEATHER_LAT/LON below, so a single-tenant deployment (today's)
    # keeps working unchanged. See weather.py::coordinates_for_current_tenant.
    WEATHER_TARGETS: str = ""

    def coordinates(self) -> Optional[tuple]:
        """(lat, lon) from WEATHER_LAT/LON, or None if not configured - the
        single-tenant fallback. See weather.py::coordinates_for_current_tenant
        for the per-tenant lookup a multi-tenant deployment needs instead."""
        if self.WEATHER_LAT is None or self.WEATHER_LON is None:
            return None
        return (self.WEATHER_LAT, self.WEATHER_LON)


class OteSettings(EnvSettings):
    """The LIDAR raw ingestion ETL (etl/ote) - see ote_etl_datamodel.md."""

    OTE_INCOMING_PREFIX: str = DEFAULT_OTE_INCOMING_PREFIX
    OTE_RAW_PREFIX: str = DEFAULT_OTE_RAW_PREFIX
    OTE_MANIFEST_PREFIX: str = DEFAULT_OTE_MANIFEST_PREFIX
    OTE_ZONES_PREFIX: str = DEFAULT_OTE_ZONES_PREFIX
    OTE_WINDOW_SECONDS: int = DEFAULT_OTE_WINDOW_SECONDS
    OTE_READ_MARGIN_SECONDS: int = DEFAULT_OTE_READ_MARGIN_SECONDS
    OTE_ARCHIVE_LOOKBACK_DAYS: int = DEFAULT_OTE_ARCHIVE_LOOKBACK_DAYS
    OTE_DOWNLOAD_WORKERS: int = DEFAULT_OTE_DOWNLOAD_WORKERS
    OTE_TRACK_GAP_SECONDS: float = DEFAULT_OTE_TRACK_GAP_SECONDS
    OTE_STATIONARY_MAX_DISPLACEMENT_M: float = DEFAULT_OTE_STATIONARY_MAX_DISPLACEMENT_M
    OTE_LABEL_ATTRS: str = DEFAULT_OTE_LABEL_ATTRS
    OTE_ZONE_ENTITY_TYPE: str = DEFAULT_OTE_ZONE_ENTITY_TYPE
    OTE_DEVICE_ENTITY_TYPE: str = DEFAULT_OTE_DEVICE_ENTITY_TYPE
    OTE_OBSERVED_ENTITY_TYPE: str = DEFAULT_OTE_OBSERVED_ENTITY_TYPE
    # Empty = discover the device ids by listing OTE_RAW_PREFIX.
    OTE_DEVICE_IDS: str = ""
    OTE_OUTPUT_DIR: str = "ote_ingest"

    def label_attrs(self) -> list:
        """The published labels, highest priority first."""
        return [label.strip() for label in self.OTE_LABEL_ATTRS.split(",") if label.strip()]

    def device_id_list(self) -> list:
        return [d.strip() for d in self.OTE_DEVICE_IDS.split(",") if d.strip()]
class AnomalySettings(EnvSettings):
    """anomaly_detection/ - one entry per datamodel, declaring what to cluster and
    the shape of that signal. ONE JSON dict and not a var per knob: they travel
    together per datamodel and separate vars drift the day one is added.

    Required per datamodel:
      measures          list of measure names to cluster on.
      cadence_minutes   how often this datamodel is expected to report. It is
                        what turns every "number of points" knob below into a
                        duration, so none of them has to be restated per datamodel.

    Optional (defaults in the DEFAULT_ANOMALY_* constants):
      calendar          which cyclic features to add: any of "hour", "weekday",
                        "month". DEFAULT EMPTY - a signal only gets the seasonality
                        it actually has, and a wrong one is pure noise diluting the
                        distance. This is what makes detection CONTEXTUAL (50 people
                        at 04:00 vs at 13:00), so an empty list means "flag by value
                        and volatility only".
      decay_days        how far back the running statistics still matter.
      rolling_hours     span of the recent-volatility window.
      regime_shift_hours  how long a sustained shift takes to be accepted as the
                        new normal instead of an anomaly.

    Example:
      ANOMALY_CONFIG={"Example": {"measures": ["measure1", "measure2"],
                                   "cadence_minutes": 60, "calendar": ["hour", "weekday"]},
                       "Example2": {"measures": ["m1"], "cadence_minutes": 1440,
                                    "calendar": ["month"], "decay_days": 120}}

    Plain str + hand-parsed JSON, NOT a Dict[str, Any] field: pydantic-settings
    DOES auto-JSON-decode a dict-typed field straight from the environment -
    verified - but ALSO tries to json.loads() an EMPTY string for that same
    field and raises before this class's own _empty_means_unset validator (or
    any field/model validator) ever runs, since that decode happens in the
    settings SOURCE, one step earlier. `ANOMALY_CONFIG=` is exactly this
    file's own "empty means unset" convention (see EnvSettings' docstring) -
    a crash on the empty/default case would defeat the whole point.
    """

    ANOMALY_CONFIG: str = ""
    ANOMALY_PREFIX: str = DEFAULT_ANOMALY_PREFIX

    def _config(self) -> dict:
        if not self.ANOMALY_CONFIG:
            return {}
        try:
            parsed = json.loads(self.ANOMALY_CONFIG)
        except json.JSONDecodeError as e:
            logger.error(f"ANOMALY_CONFIG is not valid JSON, ignoring it entirely: {e}")
            return {}
        if not isinstance(parsed, dict):
            logger.error(f"ANOMALY_CONFIG must be a JSON object keyed by datamodel, "
                         f"got {type(parsed).__name__} - ignoring it entirely.")
            return {}
        return parsed

    def _for(self, datamodel: str) -> dict:
        entry = self._config().get(datamodel, {})
        return entry if isinstance(entry, dict) else {}

    def declares_measures(self, datamodel: str) -> bool:
        """Whether the datamodel names its measures at all. ABSENT means "detect
        every numeric column"; present-but-unusable is a configuration error, and
        the two must not be confused - a typo would otherwise silently turn into
        auto-detection over columns nobody vetted."""
        return "measures" in self._for(datamodel)

    def measures_for(self, datamodel: str) -> list:
        """The configured measure names, or [] when the datamodel leaves them to
        auto-detection. A bare string is rejected rather than iterated into single
        characters, which is what list("occupancy") does."""
        measures = self._for(datamodel).get("measures", [])
        if isinstance(measures, str):
            logger.error(f"ANOMALY_CONFIG['{datamodel}']['measures'] must be a LIST, not the "
                         f"string '{measures}' - that datamodel stays disabled.")
            return []
        return [str(m) for m in measures] if isinstance(measures, (list, tuple)) else []

    def cadence_minutes_for(self, datamodel: str) -> Optional[float]:
        """How often this datamodel is expected to report. Every "number of points"
        knob (decay, rolling window, regime shift) is declared as a duration and
        converted through this, so a datamodel reporting every 5 minutes and one
        reporting daily do not need different numbers written by hand."""
        cadence = self._for(datamodel).get("cadence_minutes")
        return (float(cadence) if isinstance(cadence, (int, float))
                and not isinstance(cadence, bool) and cadence > 0 else None)

    def calendar_for(self, datamodel: str) -> list:
        """Cyclic features to add, in canonical order. Unknown names are dropped
        with a warning rather than silently changing the vector's dimension."""
        requested = self._for(datamodel).get("calendar", DEFAULT_ANOMALY_CALENDAR)
        if isinstance(requested, str):
            requested = [requested]
        if not isinstance(requested, (list, tuple)):
            return list(DEFAULT_ANOMALY_CALENDAR)
        known, unknown = [], []
        for name in requested:
            (known if name in ANOMALY_CALENDAR_CYCLES else unknown).append(name)
        if unknown:
            logger.warning(f"ANOMALY_CONFIG['{datamodel}']['calendar']: unknown cycle(s) {unknown}, "
                           f"ignored. Valid: {sorted(ANOMALY_CALENDAR_CYCLES)}")
        return [name for name in ANOMALY_CALENDAR_CYCLES if name in known]

    def _positive_number(self, datamodel: str, key: str, default: float) -> float:
        value = self._for(datamodel).get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            if key in self._for(datamodel):
                logger.warning(f"ANOMALY_CONFIG['{datamodel}']['{key}'] must be a positive "
                               f"number, got {value!r} - using {default}.")
            return float(default)
        return float(value)

    def decay_days_for(self, datamodel: str) -> float:
        return self._positive_number(datamodel, "decay_days", DEFAULT_ANOMALY_DECAY_DAYS)

    def min_measure_coverage_for(self, datamodel: str) -> float:
        return self._positive_number(datamodel, "min_measure_coverage",
                                     DEFAULT_ANOMALY_MIN_MEASURE_COVERAGE)

    def rolling_hours_for(self, datamodel: str) -> float:
        return self._positive_number(datamodel, "rolling_hours", DEFAULT_ANOMALY_ROLLING_HOURS)

    def regime_shift_hours_for(self, datamodel: str) -> float:
        return self._positive_number(datamodel, "regime_shift_hours",
                                     DEFAULT_ANOMALY_REGIME_SHIFT_HOURS)

    def is_enabled_for(self, datamodel: str) -> bool:
        """Fail CLOSED. `cadence_minutes` is always required: every "how many
        points" knob is a duration converted through it, so there is no sane
        default. `measures` is optional - absent means auto-detect - but if it IS
        declared it has to be usable, or a typo would quietly become "score
        whatever numeric column happens to be in the file"."""
        if self.cadence_minutes_for(datamodel) is None:
            return False
        return bool(self.measures_for(datamodel)) or not self.declares_measures(datamodel)




def sensors() -> SensorSettings:
    return SensorSettings()



def fusion() -> FusionSettings:
    return FusionSettings()


def storage() -> StorageSettings:
    return StorageSettings()


def fiware() -> FiwareSettings:
    return FiwareSettings()


def queue() -> QueueSettings:
    return QueueSettings()


def aether() -> AetherSettings:
    return AetherSettings()


def calendar() -> CalendarSettings:
    return CalendarSettings()


def events() -> EventSettings:
    return EventSettings()


def training() -> TrainingSettings:
    return TrainingSettings()


def prediction() -> PredictionSettings:
    return PredictionSettings()


def weather() -> WeatherSettings:
    return WeatherSettings()


def ote() -> OteSettings:
    return OteSettings()


def anomaly() -> AnomalySettings:
    return AnomalySettings()
