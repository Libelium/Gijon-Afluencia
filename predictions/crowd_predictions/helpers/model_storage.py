"""
Storage key for the model: {MODELS_PREFIX}/{tenant}/{scope}/{filename}.

The flat key it replaced had a failure mode with no error: two deployments over
the same bucket overwrote each other's model. Same scheme as parking.

The model travels as THREE files (a bundle), all under the same key prefix:
  <model>.json               the booster
  <model>.json.columns.json  the exact training columns (features + device dummies)
  <model>.json.metrics.json  MAE, hyperparameters, number of trees, mode

The third one is what makes the warm start possible: without the stored MAE
and hyperparameters there is nothing to compare a new increment against, and the
new trees would be grown with whatever the defaults happen to be that day.
"""

import json
import logging
import os

import xgboost as xgb

from crowd_predictions.config import settings

logger = logging.getLogger(__name__)

COLUMNS_SUFFIX = ".columns.json"
METRICS_SUFFIX = ".metrics.json"


class MissingSegregationError(ValueError):
    """The tenant/scope pair that segregates storage is not configured."""


def tenant_scope() -> tuple:
    """
    (tenant, scope normalized to a single key segment) of the active target.

    NO fallback: an unset pair used to land in ".../default/_/", so two badly
    configured deployments collided exactly where the segregation exists to keep
    them apart. Reads the environment on every call so helpers/fiware_targets.py
    can pin a different tenant per target.
    """
    fiware = settings.fiware()
    tenant = (fiware.FIWARE_TENANT or "").strip()
    if not tenant:
        raise MissingSegregationError(
            "FIWARE_TENANT is not set and there is no fallback: writing to '.../default/' "
            "would let two unconfigured deployments overwrite each other's model, weather "
            "cache, zones and events. Set FIWARE_TENANT (or a FIWARE_TARGETS entry)."
        )

    # The scope can arrive as "/" or "/something/other" (that is how FIWARE uses
    # it). As part of an object key, a lone "/" would create an empty segment and
    # "/a/b" would create two unexpected levels: it is normalized to a single
    # segment.
    scope = (fiware.FIWARE_SCOPE or "").strip()
    if not scope:
        raise MissingSegregationError(
            "FIWARE_SCOPE is not set and there is no fallback: it is half of the storage "
            "prefix. Use '/' if the deployment has a single scope."
        )
    return tenant, scope.strip("/").replace("/", "_") or "_"


def segregated_key(prefix: str, filename: str) -> str:
    """
    Storage key segregated by tenant/scope: {prefix}/{tenant}/{scope}/{filename}.

    Kept generic on purpose: the collision problem is the same for any file two
    deployments could write to the same bucket, not only for models.
    """
    tenant, scope_clean = tenant_scope()
    return f"{prefix.strip('/')}/{tenant}/{scope_clean}/{filename}"


def model_storage_key(filename: str) -> str:
    """Full storage key for a model file."""
    return segregated_key(settings.storage().MODELS_PREFIX, filename)


def _xgboost_save(model, path: str) -> None:
    model.save_model(path)


def _xgboost_load(path: str):
    model = xgb.XGBRegressor()
    model.load_model(path)
    return model


def save_model_bundle(storage, model_filename: str, model, train_columns: list,
                      metrics: dict, local_dir: str = "/tmp", serialize=None,
                      key_for=None) -> str:
    """
    Uploads columns + metrics + model, IN THAT ORDER. The three always together: a
    model with a stale sidecar predicts with the wrong columns and nothing complains.

    These are three uploads with no transaction, so a failure in the middle leaves a
    mixed bundle. The MODEL GOES LAST on purpose, because that makes the reachable
    half-states the harmless ones:
      - sidecars new + model old  -> the next run reads a coherent OLD bundle; at
        worst it repeats an increment or retrains in full earlier than needed.
      - model new + sidecars old  -> would predict with the wrong column set, or
        grow trees with the wrong hyperparameters. This is the order that AVOIDS it.

    `serialize(model, path)`: defaults to XGBoost's own `.save_model()` (unchanged
    behaviour for every existing caller). Pass e.g. a pickle-based function to store
    any other model type (see anomaly_detection/storage.py) - everything else here
    (sidecar JSON, upload ordering) is already model-agnostic.

    `key_for(filename) -> key`: defaults to model_storage_key (MODELS_PREFIX,
    tenant/scope-segregated). A vertical that keeps its models somewhere else passes
    its own builder; the ordering guarantee above is what it is buying by coming
    through here instead of writing the three files itself.
    """
    key_for = key_for or model_storage_key
    for suffix, payload in ((COLUMNS_SUFFIX, train_columns), (METRICS_SUFFIX, metrics)):
        filename = f"{model_filename}{suffix}"
        local_path = os.path.join(local_dir, filename)
        with open(local_path, "w") as f:
            json.dump(payload, f, default=str)
        storage.upload_file(key_for(filename), local_path)

    local_model_path = os.path.join(local_dir, model_filename)
    (serialize or _xgboost_save)(model, local_model_path)
    storage.upload_file(key_for(model_filename), local_model_path)

    return key_for(model_filename)


def load_model_bundle(storage, model_filename: str, local_dir: str = "/tmp", deserialize=None,
                      key_for=None):
    """
    (model, train_columns, metrics) or None if the bundle is not in storage - which
    is what "cold start" means: the mode is decided by the state in storage,
    not by configuration.

    An INCOMPLETE bundle also returns None: a model without its metrics sidecar
    cannot be warm-started (no hyperparameters for the new trees, no MAE to compare
    against), so it is treated as if it were not there and gets retrained in full.
    Careful, a credentials/network failure looks the same from here - hence the log
    line with the real reason.

    `deserialize(path) -> model` / `key_for(filename) -> key`: default to XGBoost's
    own reconstruction and to model_storage_key. See save_model_bundle for the
    matching write side - the two must always be given the same pair.
    """
    key_for = key_for or model_storage_key
    paths = {}
    for filename in (model_filename, f"{model_filename}{COLUMNS_SUFFIX}",
                     f"{model_filename}{METRICS_SUFFIX}"):
        local_path = os.path.join(local_dir, filename)
        try:
            storage.download_file(key_for(filename), local_path)
        except Exception as e:
            logger.info(f"No usable model in storage ('{key_for(filename)}': {e})")
            return None
        paths[filename] = local_path

    model = (deserialize or _xgboost_load)(paths[model_filename])
    with open(paths[f"{model_filename}{COLUMNS_SUFFIX}"]) as f:
        train_columns = json.load(f)
    with open(paths[f"{model_filename}{METRICS_SUFFIX}"]) as f:
        metrics = json.load(f)

    return model, train_columns, metrics
