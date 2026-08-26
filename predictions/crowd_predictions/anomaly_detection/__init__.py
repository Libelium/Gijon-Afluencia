"""
Adaptive anomaly detection (pliego §5.3), as a self-contained vertical: it knows
nothing about zones, CrowdFlowZone or CrowdFlowPrediction - only entity_id + a dict
of raw measures + a timestamp.

  core.py     the algorithm: BIRCH clustering + the running statistics around it.
  storage.py  one persisted state per entity, on helpers/model_storage.py's scheme.

The public surface is `evaluate_batch(storage, datamodel, points)`: everything else
is an implementation detail of those two modules. Callers (the ETL transforms) only
ever import from here; anything reaching for the algorithm's internals (the tests)
imports from `.core` explicitly, so that this stays a real boundary instead of a
list that has to grow every time a helper is added.
"""

from crowd_predictions.anomaly_detection.core import evaluate_batch  # noqa: F401

__all__ = ["evaluate_batch"]
