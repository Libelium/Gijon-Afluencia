"""Tests for the metrics registry — prefix enforcement and factory functions."""

import pytest

from metrics.registry import PREFIX, _name, counter, gauge, histogram, summary


# ---------------------------------------------------------------------------
# Prefix helpers
# ---------------------------------------------------------------------------


class TestName:
    def test_prepends_prefix(self):
        assert _name("celery_task_total") == f"{PREFIX}_celery_task_total"

    def test_prefix_is_platform_namespace(self):
        assert PREFIX == "pidgijon"

    def test_single_segment_name(self):
        assert _name("requests") == "pidgijon_requests"


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


class TestFactories:
    """Each factory must delegate to the correct prometheus_client class
    with the prefixed name, forwarding documentation and label names."""

    @pytest.mark.parametrize(
        ("factory_fn", "prometheus_class"),
        [
            (counter, "Counter"),
            (gauge, "Gauge"),
            (histogram, "Histogram"),
            (summary, "Summary"),
        ],
    )
    def test_applies_prefix_to_name(self, mocker, factory_fn, prometheus_class):
        mock_cls = mocker.patch(f"metrics.registry.{prometheus_class}")

        factory_fn("my_metric", "Some documentation.", ["label_a"])

        mock_cls.assert_called_once_with(
            "pidgijon_my_metric", "Some documentation.", ["label_a"]
        )

    def test_counter_forwards_empty_labels(self, mocker):
        mock_cls = mocker.patch("metrics.registry.Counter")

        counter("hits_total", "Total hits.")

        mock_cls.assert_called_once_with("pidgijon_hits_total", "Total hits.", ())

    def test_gauge_forwards_multiple_labels(self, mocker):
        mock_cls = mocker.patch("metrics.registry.Gauge")

        gauge("active_tasks", "Active tasks.", ["task_name", "worker"])

        mock_cls.assert_called_once_with(
            "pidgijon_active_tasks", "Active tasks.", ["task_name", "worker"]
        )
