"""
Adaptive anomaly detection (pliego §5.3), entity-type-agnostic: it knows nothing
about zones, occupancy or any datamodel of this repo - only entity ids, a dict of
measures and a timestamp. Everything that varies per datamodel is declared in
ANOMALY_CONFIG (see config/settings.AnomalySettings), never hardcoded here.

Algorithm: sklearn.cluster.Birch. Its Clustering Feature per subcluster is exactly
(N, LS, SS), so centroids update from a running sufficient statistic and never from
a re-read of history. Scoring uses ONLY the public subcluster_centers_ ndarray,
never Birch's private _CFSubcluster internals.

ONE MODEL PER DATAMODEL, shared by all its entities. That makes "anomalous" mean
*unlike the population of entities of this type*, not *unlike this entity's own
past* - a deliberate choice, and the reason OUTLIER_STD_MULTIPLIER is a touch
stricter than a per-entity model would need: pooling entities widens the
distribution, and normal spread between entities must not read as an anomaly.
It also means a brand-new entity inherits what the others already learnt instead of
starting blind, and that storage traffic stops scaling with the entity count.

What stays PER ENTITY inside that shared model: the recent-value window (a delta
needs *this* entity's previous value) and the idempotency watermark.

One output: isOutlier - the Birch distance against an incrementally tracked
mean/std of past distances. Never a fixed threshold.

FOUR PROPERTIES THIS MODULE HAS TO KEEP (each was a real defect once):
  1. IDEMPOTENT. A rerun re-scores but never re-trains: every entity carries a
     watermark of the last timestamp it learnt.
  2. BOUNDED. Birch's threshold scales with the dimension count and the subcluster
     count is capped - otherwise nearly every point becomes its own subcluster
     (measured: 1715 of 2000 at a fixed 0.5 in 7 dims) and both the pickle and the
     distance geometry degrade without limit.
  3. IT FORGETS. Statistics decay over a window expressed in TIME, so "adaptive"
     is still true after a year instead of decaying as 1/N.
  4. IT DOES NOT EAT ITS OWN OUTLIERS. A flagged point does not train the model,
     until enough of them in a row say it is a new normal rather than an anomaly.
"""

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
from sklearn.cluster import Birch
from sklearn.metrics import pairwise_distances_argmin_min

from crowd_predictions.config import settings

logger = logging.getLogger(__name__)

# Period of each cyclic calendar feature, in the units its accessor returns.
CALENDAR_CYCLE_PERIODS = {"hour": 24.0, "weekday": 7.0, "month": 12.0}
# Slightly stricter than a per-entity model would need - see the module docstring.
OUTLIER_STD_MULTIPLIER = 3.5
EXTREME_DIMENSION_STD_MULTIPLIER = 2.2
# 2.2 sigma on a lone dimension fires on 5.45% of pure-noise points (measured, 2
# derived dims). Requiring it twice IN A ROW drops that to 0.33% and costs nothing
# on what this check is for: a flatline or a dead sensor persists by definition.
EXTREME_DIMENSION_MIN_CONSECUTIVE = 2
# Birch's threshold is a RADIUS in the NORMALIZED space, so it grows with the
# dimension count: two independent standard-normal points sit sqrt(2n) apart.
BIRCH_THRESHOLD_PER_DIMENSION = 0.75
MAX_SUBCLUSTERS = 256
SUBCLUSTER_REBUILD_FACTOR = 1.5
# Floor for "enough history to judge", and how it grows with the dimension count:
# in more dimensions, distances concentrate and a handful of points says nothing.
MIN_POINTS_FLOOR = 10
MIN_POINTS_PER_DIMENSION = 3


@dataclass
class RunningStats:
    """Incremental mean/std. Exact (Welford) for the first `decay_window` points,
    then exponentially weighted with alpha=1/decay_window so old data FADES.
    Without decay the baseline averages all history: after months a real shift
    moves it by ~1/N and the detector is frozen. decay_window=None keeps it exact."""
    count: int = 0
    mean: float = 0.0
    _m2: float = 0.0
    _var: float = 0.0
    decay_window: Optional[int] = None

    @property
    def _decaying(self) -> bool:
        return bool(self.decay_window) and self.count >= self.decay_window

    def update(self, x: float) -> None:
        if not self._decaying:
            self.count += 1
            delta = x - self.mean
            self.mean += delta / self.count
            self._m2 += delta * (x - self.mean)
            if self._decaying:  # crossing over: seed the decaying variance
                self._var = self._m2 / self.count
            return
        alpha = 1.0 / self.decay_window
        self.count += 1
        delta = x - self.mean
        self.mean += alpha * delta
        self._var = (1 - alpha) * (self._var + alpha * delta * delta)

    @property
    def std(self) -> float:
        if self._decaying:
            return math.sqrt(self._var) if self._var > 0 else 0.0
        return math.sqrt(self._m2 / self.count) if self.count > 1 else 0.0


@dataclass
class DatamodelProfile:
    """Everything ANOMALY_CONFIG says about one datamodel, resolved once: the
    measure names, the calendar cycles, and every "number of points" knob already
    converted from the declared duration using that datamodel's own cadence.

    Resolving this in one place is what keeps the algorithm free of assumptions:
    nothing below asks how often the data arrives or what season it has."""
    datamodel: str
    measure_names: list
    calendar_cycles: list
    cadence_minutes: float
    decay_window: int
    rolling_window: int
    regime_shift_points: int

    @classmethod
    def from_settings(cls, datamodel: str, anomaly_settings=None,
                      measure_names: list = None) -> "DatamodelProfile":
        """`measure_names` overrides the config, for the auto-detection case: the
        caller is the one that has the file in front of it and can see which
        columns are numeric (see pipeline.measure_names_for)."""
        cfg = anomaly_settings or settings.anomaly()
        cadence = cfg.cadence_minutes_for(datamodel)
        per_hour = 60.0 / cadence if cadence else 1.0
        return cls(
            datamodel=datamodel,
            measure_names=list(measure_names) if measure_names else cfg.measures_for(datamodel),
            calendar_cycles=cfg.calendar_for(datamodel),
            cadence_minutes=cadence,
            # At least 2 points, or the statistic has nothing to be computed over.
            decay_window=max(2, round(cfg.decay_days_for(datamodel) * 24 * per_hour)),
            rolling_window=max(2, round(cfg.rolling_hours_for(datamodel) * per_hour)),
            regime_shift_points=max(2, round(cfg.regime_shift_hours_for(datamodel) * per_hour)),
        )

    @property
    def feature_columns(self) -> list:
        return feature_columns_for(self.measure_names, self.calendar_cycles)

    @property
    def derived_indices(self) -> list:
        return derived_indices_for(self.measure_names, self.calendar_cycles)

    @property
    def min_points_for_decision(self) -> int:
        """Grows with the dimension count: in 40 dimensions, 10 points say nothing
        about what a normal distance looks like."""
        return max(MIN_POINTS_FLOOR, MIN_POINTS_PER_DIMENSION * len(self.feature_columns))


def calendar_column_names(calendar_cycles: list) -> list:
    """['hour'] -> ['hour_sin', 'hour_cos']. Empty in, empty out: a datamodel with
    no declared seasonality gets no calendar dimensions at all."""
    return [f"{cycle}_{fn}" for cycle in calendar_cycles for fn in ("sin", "cos")]


def feature_columns_for(measure_names: list, calendar_cycles: list) -> list:
    """Exact, ORDERED columns build_feature_vector() produces. Stored as the
    bundle's columns sidecar, so any change of measures or calendar is detected
    instead of silently feeding Birch a wrong-dimension vector."""
    measures = list(measure_names)
    return (measures + calendar_column_names(calendar_cycles)
            + [f"{m}_delta" for m in measures]
            + [f"{m}_rolling_std" for m in measures])


def derived_indices_for(measure_names: list, calendar_cycles: list) -> list:
    """Positions of the DERIVED dimensions (delta, rolling_std) within the vector.

    By POSITION, computed from the block sizes - never by matching a name suffix:
    a measure legitimately called `pressure_delta` would be misread as derived, and
    would also collide with the derived column generated from it."""
    n_head = len(measure_names) + len(calendar_column_names(calendar_cycles))
    return list(range(n_head, n_head + 2 * len(measure_names)))


def calendar_row(timestamp: datetime, calendar_cycles: list) -> dict:
    """Cyclic (sin, cos) encoding of the requested cycles for ONE timestamp.

    Implemented here, over the 3 fields it needs, instead of reusing
    training_data.add_calendar_features: that one is built for the crowd training
    table, demands a `zone_id` column and drags in the holiday calendar, the events
    registry and the weather cache to produce ~15 columns of which 4 were kept.

    Timestamps are naive UTC by repo convention; the local-calendar conversion is
    the caller's business (see calendar_context)."""
    values = {"hour": timestamp.hour, "weekday": timestamp.weekday(), "month": timestamp.month - 1}
    row = {}
    for cycle in calendar_cycles:
        angle = 2 * math.pi * values[cycle] / CALENDAR_CYCLE_PERIODS[cycle]
        row[f"{cycle}_sin"] = math.sin(angle)
        row[f"{cycle}_cos"] = math.cos(angle)
    return row


def _local_calendar_timestamps(timestamps, timezone_name: str):
    """Naive-UTC series -> naive LOCAL time. Duplicated from training_data on
    purpose: importing it dragged holidays, weather and the events registry into a
    vertical that is sold as independent of the crowd one."""
    if timestamps.empty:
        return timestamps
    aware = timestamps.dt.tz_localize("UTC") if timestamps.dt.tz is None else timestamps
    return aware.dt.tz_convert(timezone_name).dt.tz_localize(None)


def calendar_context(timestamps: list, calendar_cycles: list) -> list:
    """One calendar row per timestamp, aligned BY POSITION with the input.

    Converted to the deployment's local calendar first: an hour or a weekday is a
    local-calendar concept, and at UTC+2 a Sunday 00:30 local is a Saturday 22:30
    UTC - which would label the busiest night of the week as the wrong day."""
    if not timestamps or not calendar_cycles:
        return [{} for _ in timestamps]
    import pandas as pd

    local = _local_calendar_timestamps(pd.Series(pd.to_datetime(list(timestamps))),
                                       settings.calendar().timezone())
    return [calendar_row(ts, calendar_cycles) for ts in local]


def build_feature_vector(raw_measures: dict, profile: DatamodelProfile, calendar_row_: dict,
                         window: dict) -> list:
    """raw values + calendar + delta-vs-previous + rolling-std, per measure.
    Uses `window` as it stood BEFORE this point - the caller appends afterwards -
    so delta and rolling_std never include the point being scored."""
    names = profile.measure_names
    values = [float(raw_measures[m]) for m in names]
    calendar_values = [float(calendar_row_[c])
                       for c in calendar_column_names(profile.calendar_cycles)]
    deltas = [float(raw_measures[m]) - window[m][-1] if window.get(m) else 0.0 for m in names]
    rolling_stds = [float(np.std(window[m])) if len(window.get(m, ())) >= 2 else 0.0
                    for m in names]
    return values + calendar_values + deltas + rolling_stds


def is_scorable(raw_measures: dict, measure_names: list) -> bool:
    """Whether this point can become a feature vector at all: every configured
    measure present, numeric and finite.

    NOT a judgement about the DATA - there is no rule here about what a sane value
    is (a negative one is normal for a delta, a temperature or a balance). It only
    keeps a null or a NaN out of Birch, where it would poison the centroids
    irrecoverably. An unscorable point gets no verdict and trains nothing."""
    for name in measure_names:
        value = raw_measures.get(name)
        if value is None or isinstance(value, bool):
            return False
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return False
        if not math.isfinite(numeric):
            return False
    return True


def default_birch_threshold(n_features: int) -> float:
    """Birch radius scaled to the dimension count - see BIRCH_THRESHOLD_PER_DIMENSION."""
    return BIRCH_THRESHOLD_PER_DIMENSION * math.sqrt(max(n_features, 1))


@dataclass
class DatamodelAnomalyState:
    """The persisted bundle for ONE datamodel: a single Birch model and a single
    set of running statistics shared by every entity of that type, plus the little
    that has to stay per entity.

    `feature_stats` (one RunningStats per column) z-scores each dimension before it
    reaches Birch. Without it, a subtle-magnitude dimension is swamped in raw
    Euclidean distance by whatever dimension has the largest absolute scale.

    `windows` / `watermarks` / counters are keyed by entity_id: a delta needs that
    entity's own previous value, and idempotency is per entity because entities are
    republished independently."""
    birch: Birch
    distance_stats: RunningStats = field(default_factory=RunningStats)
    feature_stats: list = field(default_factory=list)
    windows: dict = field(default_factory=dict)      # entity_id -> {measure: deque}
    watermarks: dict = field(default_factory=dict)   # entity_id -> last learnt timestamp
    consecutive_outliers: dict = field(default_factory=dict)
    consecutive_extreme: dict = field(default_factory=dict)
    birch_threshold: float = 0.0
    dirty: bool = False

    @classmethod
    def new(cls, profile: DatamodelProfile) -> "DatamodelAnomalyState":
        n_features = len(profile.feature_columns)
        threshold = default_birch_threshold(n_features)
        return cls(
            birch=Birch(n_clusters=None, threshold=threshold),
            distance_stats=RunningStats(decay_window=profile.decay_window),
            feature_stats=[RunningStats(decay_window=profile.decay_window)
                           for _ in range(n_features)],
            birch_threshold=threshold,
        )

    def window_for(self, entity_id: str, profile: DatamodelProfile) -> dict:
        window = self.windows.get(entity_id)
        if window is None:
            window = {m: deque(maxlen=profile.rolling_window) for m in profile.measure_names}
            self.windows[entity_id] = window
        return window


def normalize_vector(feature_stats: list, feature_vector: list) -> list:
    """z-score each dimension against its OWN running mean/std, as they stood
    BEFORE this point. std==0 (too few points, or a constant dimension) -> 0.0:
    nothing to compare against yet, not a division by zero."""
    return [
        (x - stats.mean) / stats.std if stats.std > 0 else 0.0
        for x, stats in zip(feature_vector, feature_stats)
    ]


def _has_extreme_dimension(state: DatamodelAnomalyState, normalized_vector: list,
                           profile: DatamodelProfile) -> bool:
    """True if any DERIVED dimension is, on its own, more than
    EXTREME_DIMENSION_STD_MULTIPLIER sigmas out. Needed ALONGSIDE the combined
    Birch distance: one volatile dimension (a rolling_std collapsing on a flatlined
    sensor) dilutes into the near-unchanged ones inside a multi-dimensional
    Euclidean distance and never crosses it.

    Raw measures are excluded on purpose - the combined distance already owns "is
    this value unusual", and re-checking it here would only compound the
    false-positive risk. Persistence keeps that risk low without blunting it."""
    eligible = set(profile.derived_indices)
    minimum = profile.min_points_for_decision
    return any(
        i in eligible and stats.count >= minimum
        and abs(z) > EXTREME_DIMENSION_STD_MULTIPLIER
        for i, (z, stats) in enumerate(zip(normalized_vector, state.feature_stats))
    )


def score_outlier(state: DatamodelAnomalyState, entity_id: str, normalized_vector: list,
                  profile: DatamodelProfile):
    """(isOutlier, distance-or-None). 1 if EITHER the combined Birch distance
    exceeds its own learned threshold, OR a derived dimension has been extreme for
    EXTREME_DIMENSION_MIN_CONSECUTIVE points in a row for this entity.

    Distance is measured against the centroids as they stood BEFORE this point -
    None only before Birch has a single centroid. It is computed as soon as one
    exists so distance_stats accumulate real numbers, while the DECISION waits for
    min_points_for_decision of them: deciding earlier compares against a threshold
    of zero, which any nonzero distance trivially exceeds."""
    streak = state.consecutive_extreme.get(entity_id, 0)
    streak = streak + 1 if _has_extreme_dimension(state, normalized_vector, profile) else 0
    state.consecutive_extreme[entity_id] = streak
    extreme = streak >= EXTREME_DIMENSION_MIN_CONSECUTIVE

    centers = getattr(state.birch, "subcluster_centers_", None)
    if centers is None or centers.size == 0:
        return int(extreme), None
    X = np.asarray([normalized_vector], dtype=float)
    _, distances = pairwise_distances_argmin_min(X, centers)
    distance = float(distances[0])
    if state.distance_stats.count < profile.min_points_for_decision:
        return int(extreme), distance
    threshold = state.distance_stats.mean + OUTLIER_STD_MULTIPLIER * state.distance_stats.std
    return int(distance > threshold or extreme), distance


def _cap_subclusters(state: DatamodelAnomalyState) -> None:
    """Rebuild Birch from its own centroids with a wider threshold once the CF tree
    passes MAX_SUBCLUSTERS. Rebuilding FROM THE CENTROIDS loses nothing that
    matters: they already are the (N, LS, SS) summary of everything seen."""
    centers = getattr(state.birch, "subcluster_centers_", None)
    if centers is None or len(centers) <= MAX_SUBCLUSTERS:
        return
    state.birch_threshold = (state.birch_threshold or state.birch.threshold) * SUBCLUSTER_REBUILD_FACTOR
    rebuilt = Birch(n_clusters=None, threshold=state.birch_threshold)
    rebuilt.partial_fit(np.asarray(centers, dtype=float))
    state.birch = rebuilt
    logger.info(f"Birch rebuilt at threshold {state.birch_threshold:.2f}: "
                f"{len(centers)} subclusters -> {len(rebuilt.subcluster_centers_)}")


def update_state(state: DatamodelAnomalyState, entity_id: str, feature_vector: list,
                 normalized_vector: list, distance, outlier: int,
                 profile: DatamodelProfile) -> None:
    """Mutates `state` in place: partial_fit on the NORMALIZED vector, then the
    running statistics with the distance and with the RAW values.

    An OUTLIER trains NOTHING: learning it raises its own threshold, so each
    further anomaly must be wilder than the last and a long anomalous episode
    anaesthetises the detector. Enough of them in a row (regime_shift_points, a
    duration in the config) are taken as a new normal and learning resumes."""
    streak = state.consecutive_outliers.get(entity_id, 0) + 1 if outlier else 0
    state.consecutive_outliers[entity_id] = streak
    if outlier and streak < profile.regime_shift_points:
        return

    state.birch.partial_fit(np.asarray([normalized_vector], dtype=float))
    _cap_subclusters(state)
    if distance is not None:
        state.distance_stats.update(distance)
    for value, stats in zip(feature_vector, state.feature_stats):
        stats.update(value)
    state.dirty = True


def evaluate_point(state: DatamodelAnomalyState, entity_id: str, raw_measures: dict,
                   calendar_row_: dict, profile: DatamodelProfile,
                   learn: bool = True) -> Optional[dict]:
    """The per-point core, or None if the point is not scorable (see is_scorable).

    learn=False scores against the current state and leaves NOTHING behind - a
    rerun of an already-processed window, or a point already seen."""
    if not is_scorable(raw_measures, profile.measure_names):
        return None

    window = state.window_for(entity_id, profile)
    feature_vector = build_feature_vector(raw_measures, profile, calendar_row_, window)
    normalized_vector = normalize_vector(state.feature_stats, feature_vector)
    extreme_before = state.consecutive_extreme.get(entity_id, 0)
    outlier, distance = score_outlier(state, entity_id, normalized_vector, profile)

    if not learn:
        state.consecutive_extreme[entity_id] = extreme_before  # a replay leaves no trace
        return {"isOutlier": outlier}

    update_state(state, entity_id, feature_vector, normalized_vector, distance, outlier, profile)
    for name in profile.measure_names:
        window[name].append(float(raw_measures[name]))

    return {"isOutlier": outlier}


def evaluate_batch(storage, datamodel: str, points: list, measure_names: list = None) -> dict:
    """
    points: [{"entity_id": str, "raw_measures": dict, "timestamp": naive UTC datetime}]

    EVERY entity of the datamodel should come in ONE call: they share a single
    model, so one call is one read-modify-write of one bundle. Splitting a
    datamodel across concurrent calls is what the lock in storage.py forbids.

    Points at or before an entity's watermark are SCORED but not learned.

    Returns {(entity_id, timestamp): {"isOutlier": int}}. Empty
    (logged, never raised) on any failure - scoring must never take down whatever
    published the data.
    """
    from crowd_predictions.anomaly_detection import storage as anomaly_storage

    if not points:
        return {}

    anomaly_settings = settings.anomaly()
    if not anomaly_settings.is_enabled_for(datamodel):
        return {}

    profile = DatamodelProfile.from_settings(datamodel, anomaly_settings, measure_names)
    if not profile.measure_names:
        logger.error(f"'{datamodel}' has no measures to score on - neither configured nor "
                     "detected. Nothing scored this run.")
        return {}

    missing = {m for m in profile.measure_names
               if not any(m in p["raw_measures"] for p in points)}
    if missing:
        logger.error(f"ANOMALY_CONFIG['{datamodel}'] names measure(s) {sorted(missing)} that no "
                     f"entity carries (available: {sorted(points[0]['raw_measures'])}) - scoring "
                     "skipped this run rather than reporting every point unscorable.")
        return {}

    try:
        calendar_rows = calendar_context([p["timestamp"] for p in points],
                                         profile.calendar_cycles)
        decorated = sorted(zip(points, calendar_rows), key=lambda pc: pc[0]["timestamp"])

        with anomaly_storage.datamodel_lock(storage, datamodel):
            state = anomaly_storage.load_state(storage, profile)
            if state is None:
                state = DatamodelAnomalyState.new(profile)

            results = {}
            # In TIMESTAMP order across the whole datamodel, not per entity: the
            # model is shared, so what it sees has to be the real chronology.
            for point, calendar_row_ in decorated:
                entity_id = point["entity_id"]
                watermark = state.watermarks.get(entity_id)
                learn = watermark is None or point["timestamp"] > watermark
                verdict = evaluate_point(state, entity_id, point["raw_measures"],
                                         calendar_row_, profile, learn=learn)
                if verdict is None:
                    logger.warning(f"{entity_id} at {point['timestamp']}: measure(s) null, "
                                   "non-numeric or infinite - point skipped, not scored.")
                    continue
                results[(entity_id, point["timestamp"])] = verdict
                if learn:
                    state.watermarks[entity_id] = point["timestamp"]
                    # dirty here too, not only in update_state: an outlier trains
                    # nothing but still moves the watermark and the streak counter.
                    state.dirty = True

            if state.dirty:
                state.dirty = False
                anomaly_storage.save_state(storage, profile, state)

        return results
    except Exception as e:
        logger.exception(f"Anomaly detection failed for datamodel '{datamodel}' - "
                         f"nothing scored this run: {e}")
        return {}
