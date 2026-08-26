"""
Metrics module for exposing Celery worker metrics via Prometheus.

Usage:
    Call `setup()` once during worker startup (done in config/celery.py).
    Metrics are exposed on port 8000 (HTTP, Prometheus scrape format).

Extending:
    To add task-specific metrics, create a new Collector subclass in
    `collectors/` and register it inside `_register_collectors()`.
"""

from metrics.collectors import register_default_collectors
from metrics.server import start_server


def setup() -> None:
    """Wire up metric collectors and start the HTTP server when the worker is ready."""
    from celery.signals import worker_process_shutdown, worker_ready

    register_default_collectors()
    worker_ready.connect(start_server, weak=False)
    worker_process_shutdown.connect(_on_worker_process_shutdown, weak=False)


def _on_worker_process_shutdown(**kwargs) -> None:
    import os
    from config.logging import appLogging as logging

    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if not multiproc_dir:
        return

    try:
        from prometheus_client import multiprocess
        multiprocess.mark_process_dead(os.getpid())
    except Exception as e:
        logging.error(f"[metrics] Failed to mark process dead: {e}", exc_info=True)
