"""Tests for the metrics HTTP server startup."""

import pytest

from metrics.server import start_server


class TestStartServer:
    def test_starts_on_settings_port(self, mocker):
        mock_settings = mocker.patch("metrics.server.settings")
        mock_settings.METRICS_PORT = 8000
        mock_settings.PROMETHEUS_MULTIPROC_DIR = ""
        mocker.patch("prometheus_client.multiprocess.MultiProcessCollector")
        mock_start = mocker.patch("prometheus_client.start_http_server")

        start_server()

        mock_start.assert_called_once()
        assert mock_start.call_args[0][0] == 8000

    def test_does_not_raise_when_port_already_in_use(self, mocker):
        mock_settings = mocker.patch("metrics.server.settings")
        mock_settings.METRICS_PORT = 8000
        mock_settings.PROMETHEUS_MULTIPROC_DIR = ""
        mocker.patch("prometheus_client.multiprocess.MultiProcessCollector")
        mocker.patch(
            "prometheus_client.start_http_server",
            side_effect=OSError("address already in use"),
        )

        start_server()  # must not propagate the error

    def test_logs_info_on_successful_start(self, mocker):
        mock_settings = mocker.patch("metrics.server.settings")
        mock_settings.METRICS_PORT = 8000
        mock_settings.PROMETHEUS_MULTIPROC_DIR = ""
        mocker.patch("prometheus_client.multiprocess.MultiProcessCollector")
        mocker.patch("prometheus_client.start_http_server")
        mock_log = mocker.patch("metrics.server.logging")

        start_server()

        mock_log.info.assert_called()

    def test_logs_warning_on_port_conflict(self, mocker):
        mock_settings = mocker.patch("metrics.server.settings")
        mock_settings.METRICS_PORT = 8000
        mock_settings.PROMETHEUS_MULTIPROC_DIR = ""
        mocker.patch("prometheus_client.multiprocess.MultiProcessCollector")
        mocker.patch("prometheus_client.start_http_server", side_effect=OSError)
        mock_log = mocker.patch("metrics.server.logging")

        start_server()

        mock_log.warning.assert_called_once()
