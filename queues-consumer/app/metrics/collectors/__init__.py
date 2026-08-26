"""
Collector registry.

Add new Collector instances here to activate them for every worker.
Task-specific collectors should also be registered here once implemented.
"""

from metrics.collectors.sync_metrics import SyncMetricsCollector
from metrics.collectors.task_metrics import TaskMetricsCollector


def register_default_collectors() -> None:
    """Instantiate and register all default metric collectors."""
    TaskMetricsCollector().register()
    SyncMetricsCollector().register()
