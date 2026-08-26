"""Tests for TaskMetricsCollector — default Celery task metrics."""

import time

import pytest
from unittest.mock import MagicMock

from metrics.collectors.task_metrics import TaskMetricsCollector, _start_times


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_start_times():
    """Guarantee a clean _start_times state for every test."""
    _start_times.clear()
    yield
    _start_times.clear()


@pytest.fixture
def collector():
    return TaskMetricsCollector()


@pytest.fixture
def mock_task():
    task = MagicMock()
    task.name = "platform.test.task"
    return task


# ---------------------------------------------------------------------------
# register()
# ---------------------------------------------------------------------------


class TestRegister:
    def test_connects_prerun_signal(self, mocker, collector):
        mock_prerun = mocker.patch("metrics.collectors.task_metrics.task_prerun")
        mocker.patch("metrics.collectors.task_metrics.task_postrun")
        mocker.patch("metrics.collectors.task_metrics.task_retry")

        collector.register()

        mock_prerun.connect.assert_called_once_with(collector._on_prerun, weak=False)

    def test_connects_postrun_signal(self, mocker, collector):
        mocker.patch("metrics.collectors.task_metrics.task_prerun")
        mock_postrun = mocker.patch("metrics.collectors.task_metrics.task_postrun")
        mocker.patch("metrics.collectors.task_metrics.task_retry")

        collector.register()

        mock_postrun.connect.assert_called_once_with(collector._on_postrun, weak=False)

    def test_connects_retry_signal(self, mocker, collector):
        mocker.patch("metrics.collectors.task_metrics.task_prerun")
        mocker.patch("metrics.collectors.task_metrics.task_postrun")
        mock_retry = mocker.patch("metrics.collectors.task_metrics.task_retry")

        collector.register()

        mock_retry.connect.assert_called_once_with(collector._on_retry, weak=False)


# ---------------------------------------------------------------------------
# _on_prerun
# ---------------------------------------------------------------------------


class TestOnPrerun:
    def test_records_start_time(self, mocker, collector, mock_task):
        mocker.patch("metrics.collectors.task_metrics.tasks_active")

        collector._on_prerun(task_id="task-001", task=mock_task)

        assert "task-001" in _start_times

    def test_increments_active_gauge(self, mocker, collector, mock_task):
        mock_gauge = mocker.patch("metrics.collectors.task_metrics.tasks_active")

        collector._on_prerun(task_id="task-001", task=mock_task)

        mock_gauge.labels.assert_called_once_with(task_name=mock_task.name)
        mock_gauge.labels.return_value.inc.assert_called_once()

    def test_start_time_is_recent(self, mocker, collector, mock_task):
        mocker.patch("metrics.collectors.task_metrics.tasks_active")
        before = time.monotonic()

        collector._on_prerun(task_id="task-001", task=mock_task)

        assert _start_times["task-001"] >= before


# ---------------------------------------------------------------------------
# _on_postrun
# ---------------------------------------------------------------------------


class TestOnPostrun:
    def test_observes_duration_histogram(self, mocker, collector, mock_task):
        mock_histogram = mocker.patch("metrics.collectors.task_metrics.task_duration")
        mocker.patch("metrics.collectors.task_metrics.tasks_active")
        mocker.patch("metrics.collectors.task_metrics.task_total")
        _start_times["task-001"] = time.monotonic() - 1.0  # 1 second ago

        collector._on_postrun(task_id="task-001", task=mock_task, state="SUCCESS")

        mock_histogram.labels.assert_called_once_with(task_name=mock_task.name)
        observed = mock_histogram.labels.return_value.observe.call_args[0][0]
        assert observed >= 1.0

    def test_removes_start_time_after_completion(self, mocker, collector, mock_task):
        mocker.patch("metrics.collectors.task_metrics.task_duration")
        mocker.patch("metrics.collectors.task_metrics.tasks_active")
        mocker.patch("metrics.collectors.task_metrics.task_total")
        _start_times["task-001"] = time.monotonic()

        collector._on_postrun(task_id="task-001", task=mock_task, state="SUCCESS")

        assert "task-001" not in _start_times

    def test_decrements_active_gauge(self, mocker, collector, mock_task):
        mocker.patch("metrics.collectors.task_metrics.task_duration")
        mock_gauge = mocker.patch("metrics.collectors.task_metrics.tasks_active")
        mocker.patch("metrics.collectors.task_metrics.task_total")
        _start_times["task-001"] = time.monotonic()

        collector._on_postrun(task_id="task-001", task=mock_task, state="SUCCESS")

        mock_gauge.labels.assert_called_once_with(task_name=mock_task.name)
        mock_gauge.labels.return_value.dec.assert_called_once()

    @pytest.mark.parametrize(
        ("celery_state", "expected_label"),
        [
            ("SUCCESS", "success"),
            ("FAILURE", "failure"),
        ],
    )
    def test_increments_task_total_with_correct_state(
        self, mocker, collector, mock_task, celery_state, expected_label
    ):
        mocker.patch("metrics.collectors.task_metrics.task_duration")
        mocker.patch("metrics.collectors.task_metrics.tasks_active")
        mock_counter = mocker.patch("metrics.collectors.task_metrics.task_total")
        _start_times["task-001"] = time.monotonic()

        collector._on_postrun(task_id="task-001", task=mock_task, state=celery_state)

        mock_counter.labels.assert_called_once_with(
            task_name=mock_task.name, state=expected_label
        )
        mock_counter.labels.return_value.inc.assert_called_once()

    def test_skips_histogram_when_start_time_unknown(self, mocker, collector, mock_task):
        """Postrun for a task with no prerun entry must not crash or record duration."""
        mock_histogram = mocker.patch("metrics.collectors.task_metrics.task_duration")
        mocker.patch("metrics.collectors.task_metrics.tasks_active")
        mocker.patch("metrics.collectors.task_metrics.task_total")

        collector._on_postrun(task_id="unknown-id", task=mock_task, state="SUCCESS")

        mock_histogram.labels.return_value.observe.assert_not_called()


# ---------------------------------------------------------------------------
# _on_retry
# ---------------------------------------------------------------------------


class TestOnRetry:
    def test_increments_retry_counter(self, mocker, collector):
        mock_counter = mocker.patch("metrics.collectors.task_metrics.task_total")
        mock_request = MagicMock()
        mock_request.task = "platform.test.task"

        collector._on_retry(request=mock_request)

        mock_counter.labels.assert_called_once_with(
            task_name="platform.test.task", state="retry"
        )
        mock_counter.labels.return_value.inc.assert_called_once()

    def test_uses_unknown_when_task_attr_missing(self, mocker, collector):
        """Requests without a .task attribute must not raise."""
        mock_counter = mocker.patch("metrics.collectors.task_metrics.task_total")
        mock_request = MagicMock(spec=[])  # no attributes at all

        collector._on_retry(request=mock_request)

        mock_counter.labels.assert_called_once_with(task_name="unknown", state="retry")
