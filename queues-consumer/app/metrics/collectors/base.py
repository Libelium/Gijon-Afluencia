"""Base interface for all metric collectors."""

from abc import ABC, abstractmethod


class Collector(ABC):
    """
    A Collector encapsulates a cohesive set of related metrics and the
    Celery signal handlers that populate them.

    Subclass this for each logical group of metrics (e.g. default task
    metrics, HTTP connector metrics, ETL metrics, …).

    Example::

        class MyTaskCollector(Collector):
            _my_counter = Counter("my_metric_total", "...", ["task_name"])

            def register(self) -> None:
                task_postrun.connect(self._on_postrun)

            def _on_postrun(self, task, **kwargs) -> None:
                self._my_counter.labels(task_name=task.name).inc()
    """

    @abstractmethod
    def register(self) -> None:
        """Connect Celery signals and initialise any required state."""
        ...
