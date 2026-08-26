"""HTTP server that exposes Prometheus metrics on a dedicated port."""

from config.config import settings
from config.logging import appLogging as logging


def start_server(**kwargs) -> None:
    """
    Start the Prometheus HTTP metrics server.

    Uses MultiProcessCollector so metrics written by Celery child processes
    (prefork pool) are aggregated and visible at scrape time.

    Safe to call multiple times: if the port is already bound (e.g. a second
    worker process on the same host), the error is logged and ignored so the
    worker continues normally.
    """
    from prometheus_client import CollectorRegistry, start_http_server
    from prometheus_client.multiprocess import MultiProcessCollector

    port = settings.METRICS_PORT
    multiproc_dir = settings.PROMETHEUS_MULTIPROC_DIR or None
    logging.info(f"[metrics] PROMETHEUS_MULTIPROC_DIR={multiproc_dir!r}")

    try:
        registry = CollectorRegistry()
        MultiProcessCollector(registry, path=multiproc_dir)
        start_http_server(port, registry=registry)
        logging.info(f"[metrics] Server started on port {port}")
    except OSError:
        logging.warning(
            f"[metrics] Port {port} already in use — skipping server start "
            "(expected when running multiple worker processes)"
        )
    except Exception as e:
        logging.error(f"[metrics] Failed to start server: {e}", exc_info=True)
