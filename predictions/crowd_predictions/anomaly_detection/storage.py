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

SEC-019 - why the pickle stays, and what guards it now
------------------------------------------------------
`pickle.load` is not a parser, it is an interpreter: a crafted file runs arbitrary
code in this process. The bundle is read from
`anomalies_detection/{tenant}/{scope}/models/anomaly_<datamodel>.pkl`, so write
access to that bucket prefix - a leaked key, a misconfigured policy, another
tenant, a compromised pod - was remote code execution in the prediction worker.
The finding is a reappearance (SEC-001 of the first delivery).

Replacing the format was considered and rejected on the evidence, not on
convenience. The bundle holds a live `sklearn.cluster.Birch`, and the vertical
LEARNS incrementally through `partial_fit`, which needs Birch's CF-tree:
`root_`, `dummy_leaf_` and the `_CFNode` / `_CFSubcluster` chain, all private
sklearn internals with no public accessor and no stable layout. Scoring alone
would need only the public `subcluster_centers_` ndarray, so a JSON/parquet
bundle could score - but it could not continue training, which is the whole
design (see core.py: "instead of a re-read of history"). Writing a JSON codec for
sklearn's private tree means reimplementing it and re-verifying it on every
sklearn bump - strictly more fragile than the pickle it replaced, and this file
already detects a version mismatch and retrains.

So the control applied is integrity, which is what the threat actually needs:

  1. Every bundle carries an HMAC-SHA256 over its own bytes, keyed by
     ANOMALY_STATE_HMAC_KEY. A file this deployment did not write does not
     verify, and is never handed to the unpickler.
  2. Defence in depth: verification passed, deserialization still goes through a
     restricted Unpickler that resolves only the handful of classes this bundle
     legitimately contains. A signed-but-hostile payload (i.e. the key itself
     leaked) still cannot reach `os.system` or `subprocess.Popen`.
  3. Fail-closed and cheap: an unsigned bundle, a bad signature or an
     unconfigured key all raise, and `load_state` already turns any read failure
     into "start a fresh model". The cost of refusing is a retrain, not an outage,
     which is why there is no "load it anyway" path.

Rotating the key invalidates every stored bundle: the datamodels retrain. That is
intended - it is also the recovery procedure if a bundle is ever suspect.
"""

import hashlib
import hmac
import io
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


# Framing of a stored bundle: MAGIC || HMAC-SHA256(payload) || payload.
# Keeping the signature inside the object rather than in a fourth sidecar file
# preserves save_model_bundle's "model last" upload ordering, which is what makes
# the reachable half-states harmless.
_BUNDLE_MAGIC = b"PIDANOM1"
_HMAC_SIZE = hashlib.sha256().digest_size


class UnsignedBundleError(ValueError):
    """The stored bundle has no valid signature, so it is not ours to trust."""


class DisallowedBundleClassError(ValueError):
    """The bundle references a class an anomaly bundle has no business containing."""


# Exactly what a DatamodelAnomalyState graph legitimately resolves to. Derived by
# recording every find_class() call while loading a real round-tripped bundle, not
# guessed - see tests/test_anomaly_storage_security.py, which fails if the graph
# ever needs something not listed here (rather than silently widening).
_ALLOWED_CLASSES = {
    ("crowd_predictions.anomaly_detection.core", "DatamodelAnomalyState"),
    ("crowd_predictions.anomaly_detection.core", "RunningStats"),
    ("sklearn.cluster._birch", "Birch"),
    ("sklearn.cluster._birch", "_CFNode"),
    ("sklearn.cluster._birch", "_CFSubcluster"),
    ("collections", "deque"),
    # Watermarks and rolling windows hold instants. A naive datetime needs only
    # `datetime.datetime`; a tz-aware one also resolves `timezone` and
    # `timedelta`, so all three are listed rather than waiting for the first
    # aware watermark to refuse a bundle in production. All three are pure data
    # constructors with no side effects.
    ("datetime", "datetime"),
    ("datetime", "timezone"),
    ("datetime", "timedelta"),
    ("numpy", "ndarray"),
    ("numpy", "dtype"),
    # numpy reorganised these into `numpy._core` in 2.0 and the project allows
    # numpy>=1.24,<3, so BOTH spellings have to resolve or a bundle written under
    # one major cannot be read under the other. Which of them a given array uses
    # is a numpy internal detail: a contiguous array pickles through
    # `_frombuffer`, a scalar through `scalar`, an F-ordered or sliced one
    # through `_reconstruct`.
    ("numpy._core.multiarray", "_reconstruct"),
    ("numpy._core.multiarray", "scalar"),
    ("numpy._core.numeric", "_frombuffer"),
    ("numpy.core.multiarray", "_reconstruct"),
    ("numpy.core.multiarray", "scalar"),
    ("numpy.core.numeric", "_frombuffer"),
}


class _RestrictedUnpickler(pickle.Unpickler):
    """Resolves only the classes in _ALLOWED_CLASSES.

    This is the layer that survives a leaked HMAC key. `pickle`'s dangerous
    primitives all arrive through the GLOBAL/STACK_GLOBAL opcodes, i.e. through
    find_class, so refusing there refuses `posix.system`, `builtins.eval`,
    `subprocess.Popen` and every other gadget.
    """

    def find_class(self, module: str, name: str):
        if (module, name) not in _ALLOWED_CLASSES:
            raise DisallowedBundleClassError(
                f"anomaly bundle references {module}.{name}, which is not allowed"
            )
        return super().find_class(module, name)


def _hmac_key() -> bytes:
    key = (settings.anomaly().ANOMALY_STATE_HMAC_KEY or "").encode("utf-8")
    if not key:
        raise UnsignedBundleError(
            "ANOMALY_STATE_HMAC_KEY is not configured, so the anomaly bundle can "
            "neither be signed nor verified. Set it (any long random string, the "
            "same value on every replica) - an unsigned bundle is not loaded."
        )
    return key


def _sign(payload: bytes) -> bytes:
    return hmac.new(_hmac_key(), payload, hashlib.sha256).digest()


def _pickle_save(state, path: str) -> None:
    payload = pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL)
    with open(path, "wb") as f:
        f.write(_BUNDLE_MAGIC)
        f.write(_sign(payload))
        f.write(payload)


def _pickle_load(path: str):
    with open(path, "rb") as f:
        blob = f.read()

    header = len(_BUNDLE_MAGIC) + _HMAC_SIZE
    if len(blob) < header or not blob.startswith(_BUNDLE_MAGIC):
        # Includes every bundle written before this change: they are unsigned, so
        # they are refused and the datamodel retrains once.
        raise UnsignedBundleError(
            "anomaly bundle is not in the signed format - refusing to unpickle it"
        )

    signature = blob[len(_BUNDLE_MAGIC):header]
    payload = blob[header:]

    # compare_digest, not ==, so a wrong signature does not leak its prefix.
    if not hmac.compare_digest(signature, _sign(payload)):
        raise UnsignedBundleError(
            "anomaly bundle signature does not verify - refusing to unpickle it"
        )

    return _RestrictedUnpickler(io.BytesIO(payload)).load()


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
