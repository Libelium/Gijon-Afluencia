"""
Persists ONE anomaly bundle per datamodel (see core.DatamodelAnomalyState), on top
of helpers/model_storage.py's storage-key scheme: tenant/scope segregation, columns
and metrics sidecars, and the "model last" upload order.

One bundle per datamodel, not per entity: every entity of a type shares the model,
so a run is a single read-modify-write however many entities it covers. That is
also why it needs a lock - see datamodel_lock().

Via pickle, since there is no XGBoost-style save_model() for a Birch + running
statistics bundle and it only ever round-trips through this code. Pickling a
sklearn estimator IS version-fragile, which is why the sklearn version travels in
the metrics sidecar and a mismatch starts fresh instead of unpickling blind.
"""

import json
import logging
import os
import pickle
import time
import uuid
from contextlib import contextmanager

import sklearn

from crowd_predictions.anomaly_detection.core import DatamodelAnomalyState
from crowd_predictions.config import settings
from crowd_predictions.helpers.model_storage import (METRICS_SUFFIX, load_model_bundle,
                                                     save_model_bundle, segregated_key)

logger = logging.getLogger(__name__)

# A lock older than this is treated as abandoned (a pod killed mid-run), never as a
# run still going: without expiry, one crash would block the datamodel for ever.
LOCK_STALE_SECONDS = 3600
LOCK_SUFFIX = ".lock.json"


def anomaly_root() -> str:
    """`anomalies_detection` (configurable). Everything the vertical reads or
    writes hangs off it, tenant/scope-segregated by segregated_key()."""
    return settings.anomaly().ANOMALY_PREFIX


def anomaly_key(*parts: str) -> str:
    """A key under this tenant/scope's own anomaly root:
    anomalies_detection/{tenant}/{scope}/<parts...>"""
    return segregated_key(anomaly_root(), "/".join(parts))


def anomaly_model_filename(datamodel: str) -> str:
    """One bundle per datamodel. No entity in the name, so nothing can collide the
    way per-entity files did when two URNs shared their last segment."""
    return f"anomaly_{datamodel}.pkl"


def model_key(filename: str) -> str:
    return anomaly_key("models", filename)


def _pickle_save(state, path: str) -> None:
    with open(path, "wb") as f:
        pickle.dump(state, f)


def _pickle_load(path: str):
    with open(path, "rb") as f:
        return pickle.load(f)


def save_state(storage, profile, state: DatamodelAnomalyState, local_dir: str = "/tmp") -> str:
    metrics = {"n_points": state.distance_stats.count,
               "distance_mean": state.distance_stats.mean,
               "distance_std": state.distance_stats.std,
               "birch_threshold": state.birch_threshold,
               "n_subclusters": len(getattr(state.birch, "subcluster_centers_", [])),
               "n_entities": len(state.watermarks),
               "measures": list(profile.measure_names),
               "cadence_minutes": profile.cadence_minutes,
               "decay_window": profile.decay_window,
               "calendar": list(profile.calendar_cycles),
               "sklearn_version": sklearn.__version__}
    return save_model_bundle(storage, anomaly_model_filename(profile.datamodel), state,
                             profile.feature_columns, metrics, local_dir=local_dir,
                             serialize=_pickle_save, key_for=model_key)


def stored_measure_names(storage, datamodel: str, local_dir: str = "/tmp") -> list:
    """The measure set the stored model was built on, or [] if there is no model yet.

    Read from the metrics sidecar alone, without unpickling anything: the caller
    only needs to know whether the set is already frozen. This is what stops an
    auto-detected measure set from being silently redefined by a file that happens
    to carry one column fewer - which would not degrade the model, it would RESET
    it, and with one model per datamodel that is every entity at once."""
    filename = f"{anomaly_model_filename(datamodel)}{METRICS_SUFFIX}"
    path = os.path.join(local_dir, filename)
    try:
        storage.download_file(model_key(filename), path)
        with open(path) as f:
            return list(json.load(f).get("measures", []))
    except Exception:
        return []


def load_state(storage, profile, local_dir: str = "/tmp"):
    """The persisted state, or None - nothing stored yet, a storage error, a
    corrupt/foreign pickle, or a configuration whose columns no longer match.

    All of them start the datamodel fresh rather than crash or feed Birch a
    wrong-dimension vector. Note what a fresh start costs here: with one model per
    datamodel it is EVERY entity's history at once, so a change to `measures` or
    `calendar` is a real retrain, not a per-entity blip."""
    try:
        result = load_model_bundle(storage, anomaly_model_filename(profile.datamodel),
                                   local_dir=local_dir, deserialize=_pickle_load,
                                   key_for=model_key)
    except Exception as e:
        # Raised OUTSIDE model_storage's own try, which only covers the download.
        # Without catching it here the bundle is never overwritten and the
        # datamodel stays dead on every future run.
        logger.warning(f"{profile.datamodel}: stored anomaly state could not be read ({e}) - "
                       "starting a fresh model for this datamodel.")
        return None
    if result is None:
        return None

    state, stored_columns, metrics = result
    if stored_columns != profile.feature_columns:
        logger.warning(f"{profile.datamodel}: anomaly feature set changed "
                       f"({stored_columns} -> {profile.feature_columns}) - starting a fresh "
                       "model. Every entity of this datamodel relearns from scratch.")
        return None
    stored_version = (metrics or {}).get("sklearn_version")
    if stored_version != sklearn.__version__:
        logger.warning(f"{profile.datamodel}: state written by sklearn {stored_version}, running "
                       f"{sklearn.__version__} - starting a fresh model for this datamodel.")
        return None
    return state


def _lock_key(datamodel: str) -> str:
    return model_key(f"{anomaly_model_filename(datamodel)}{LOCK_SUFFIX}")


def _read_lock(storage, datamodel: str, local_dir: str):
    path = os.path.join(local_dir, f"anomaly_{datamodel}{LOCK_SUFFIX}")
    try:
        storage.download_file(_lock_key(datamodel), path)
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None  # absent, unreadable or unparseable -> treat as not held


def _write_lock(storage, datamodel: str, payload: dict, local_dir: str) -> None:
    path = os.path.join(local_dir, f"anomaly_{datamodel}{LOCK_SUFFIX}.{uuid.uuid4().hex}")
    with open(path, "w") as f:
        json.dump(payload, f)
    storage.upload_file(_lock_key(datamodel), path)


class DatamodelLocked(RuntimeError):
    """Another run holds this datamodel. Its own type so a caller can skip the run
    quietly instead of treating it as a failure."""


@contextmanager
def datamodel_lock(storage, datamodel: str, local_dir: str = "/tmp"):
    """Serialises runs OF THE SAME DATAMODEL, so two of them cannot read the same
    bundle, learn different points and have the last writer erase the other.

    Every entity of the datamodel is meant to be processed INSIDE one lock, in a
    single call - that is the supported parallelism, and it is why evaluate_batch
    takes all the points at once.

    ⚠️ ADVISORY, not a mutex. It is built on plain upload/download, which give no
    atomic create-if-absent, so two runs starting within the same instant can both
    believe they took it. It closes the realistic window (a cron overlapping its own
    previous run, a retry landing on top of a slow one), not a genuine race. The
    real guarantee has to come from not scheduling a datamodel concurrently.
    """
    holder = uuid.uuid4().hex
    existing = _read_lock(storage, datamodel, local_dir)
    # holder=None is the marker a clean release leaves behind: free, not abandoned.
    if existing and existing.get("holder"):
        age = time.time() - existing.get("acquired_at", 0)
        if age < LOCK_STALE_SECONDS:
            raise DatamodelLocked(
                f"'{datamodel}' is locked by run {existing.get('holder')} since "
                f"{int(age)}s ago - skipping this run rather than racing it.")
        logger.warning(f"'{datamodel}': lock from run {existing.get('holder')} is "
                       f"{int(age)}s old, past {LOCK_STALE_SECONDS}s - assuming that run died "
                       "and taking it over.")

    _write_lock(storage, datamodel, {"holder": holder, "acquired_at": time.time()}, local_dir)
    try:
        yield holder
    finally:
        # Released by marking it free, not by deleting: delete_file is not part of
        # every StorageType in the same shape, and an expired marker reads as free
        # anyway.
        try:
            _write_lock(storage, datamodel, {"holder": None, "acquired_at": 0}, local_dir)
        except Exception as e:
            logger.warning(f"'{datamodel}': could not release the lock ({e}). It expires on "
                           f"its own in {LOCK_STALE_SECONDS}s.")
