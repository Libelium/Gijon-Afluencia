"""
Default task-level metrics collected for every Celery task.

Metrics exposed
---------------
celery_task_duration_seconds  Histogram  How long each task took to run.
celery_task_total             Counter    Tasks completed, labelled by state
                                         (success / failure / retry).
celery_tasks_active           Gauge      Tasks currently executing.
"""

import time

from celery.signals import task_postrun, task_prerun, task_retry

from config.logging import appLogging as logging
from metrics.collectors.base import Collector
from metrics.registry import counter, gauge, histogram

# ---------------------------------------------------------------------------
# Metric definitions (module-level so they are registered with the default
# Prometheus registry exactly once, regardless of how many workers share it).
# ---------------------------------------------------------------------------

task_duration = histogram(
    "celery_task_duration_seconds",
    "Wall-clock time from task start to task completion, in seconds.",
    ["task_name"],
)

task_total = counter(
    "celery_task_total",
    "Total number of task executions, labelled by outcome state "
    "(success, failure, retry).",
    ["task_name", "state"],
)

tasks_active = gauge(
    "celery_tasks_active",
    "Number of tasks currently being executed by this worker.",
    ["task_name"],
)

# Maps task_id → monotonic start time while the task is running.
_start_times: dict[str, float] = {}


class TaskMetricsCollector(Collector):
    """Connects Celery signals to the default task metrics."""

    def register(self) -> None:
        task_prerun.connect(self._on_prerun, weak=False)
        task_postrun.connect(self._on_postrun, weak=False)
        task_retry.connect(self._on_retry, weak=False)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_prerun(self, task_id: str, task, **kwargs) -> None:
        try:
            _start_times[task_id] = time.monotonic()
            tasks_active.labels(task_name=task.name).inc()
        except Exception as e:
            logging.error(f"[metrics] _on_prerun failed: {e}", exc_info=True)

    def _on_postrun(self, task_id: str, task, state: str, **kwargs) -> None:
        try:
            start = _start_times.pop(task_id, None)
            if start is not None:
                task_duration.labels(task_name=task.name).observe(
                    time.monotonic() - start
                )

            tasks_active.labels(task_name=task.name).dec()

            # state comes from Celery as "SUCCESS" or "FAILURE";
            # may be None when a hard time limit kills the task before it finishes.
            task_total.labels(task_name=task.name, state=(state or "timeout").lower()).inc()
        except Exception as e:
            logging.error(f"[metrics] _on_postrun failed: {e}", exc_info=True)

    def _on_retry(self, request, **kwargs) -> None:
        try:
            # `request` is a celery.app.trace.TraceInfo-like object; `.task` holds
            # the dotted task name when available.
            task_name = getattr(request, "task", "unknown")
            task_total.labels(task_name=task_name, state="retry").inc()
        except Exception as e:
            logging.error(f"[metrics] _on_retry failed: {e}", exc_info=True)
