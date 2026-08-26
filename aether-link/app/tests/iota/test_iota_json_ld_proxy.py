from typing import List, Union
import pytest
from unittest.mock import MagicMock, patch

from app.core.iota.iota_proxy.iota_json_proxy.iota_json_ld_proxy import IOTAJsonLdProxy
from aether_pylib.iota.delete_devices_request import DeleteDevicesRequest
from aether_pylib.iota.delete_devices_result import (
    DeleteDevicesResult,
    DeviceBatchOperationError,
)
import requests

@pytest.fixture
def iota_proxy_config():
    return {
        "IOTA_JSON_URL": "http://iota-json:4041",
        "DEFAULT_TENANT": "gijon",
    }


@pytest.fixture
def iota_proxy(iota_proxy_config):
    return IOTAJsonLdProxy(**iota_proxy_config)


class TestIOTAJsonLdProxy:

    @patch("requests.Session.delete")
    @pytest.mark.parametrize(
        ("delete_request", "mock_responses", "expected_result"),
        [
            # Case 1: Succesfull delete
            (
                DeleteDevicesRequest(devices_serials=["device_001"]),
                [
                    MagicMock(status_code=204, text=""),
                ],
                DeleteDevicesResult(devices=["device_001"], errors=[]),
            ),
            # Case 2: Device not found
            (
                DeleteDevicesRequest(devices_serials=["device_002"]),
                [
                    MagicMock(status_code=404, text="Device not found"),
                ],
                DeleteDevicesResult(
                    devices=[],
                    errors=[
                        DeviceBatchOperationError(
                            id="device_002",
                            error={"message": "Device not found", "status": 404},
                        )
                    ],
                ),
            ),
            # Case 3: Multiple devices
            (
                DeleteDevicesRequest(devices_serials=["device_003", "device_004"]),
                [
                    MagicMock(status_code=204, text=""),
                    MagicMock(status_code=404, text="Device not found"),
                ],
                DeleteDevicesResult(
                    devices=["device_003"],
                    errors=[
                        DeviceBatchOperationError(
                            id="device_004",
                            error={"message": "Device not found", "status": 404},
                        )
                    ],
                ),
            ),
            # Case 4: 500 Internal Server Error
            (
                DeleteDevicesRequest(devices_serials=["device_005"]),
                [
                    MagicMock(status_code=500, text="Internal Server Error"),
                ],
                DeleteDevicesResult(
                    devices=[],
                    errors=[
                        DeviceBatchOperationError(
                            id="device_005",
                            error={
                                "message": "Error deleting device: Internal Server Error",
                                "status": 500,
                            },
                        )
                    ],
                ),
            ),
            # Case 5: Network error
            (
                DeleteDevicesRequest(devices_serials=["device_006"]),
                [
                    requests.exceptions.RequestException("Connection refused"),
                ],
                DeleteDevicesResult(
                    devices=[],
                    errors=[
                        DeviceBatchOperationError(
                            id="device_006",
                            error={
                                "message": "Network or connection error: Connection refused",
                                "status": 500,
                            },
                        )
                    ],
                ),
            ),
            # Case 6: Empty list of devices
            (
                DeleteDevicesRequest(devices_serials=[]),
                [],
                DeleteDevicesResult(devices=[], errors=[]),
            ),
        ],
    )
    def test_delete_devices(
        self,
        mock_session_delete: MagicMock,
        delete_request: DeleteDevicesRequest,
        mock_responses: List[Union[MagicMock, requests.exceptions.RequestException]],
        expected_result: DeleteDevicesResult,
        iota_proxy: IOTAJsonLdProxy,
    ):
        """
        Verifies the behavior of the delete_devices method under various scenarios.
        """
        mock_session_delete.side_effect = mock_responses
        scopeDefault = "/"

        result = iota_proxy.delete_devices(
            delete_request, iota_proxy.tenant, scopeDefault
        )

        assert result == expected_result

        if not any(
            isinstance(mr, requests.exceptions.RequestException)
            for mr in mock_responses
        ):
            expected_calls = []
            for device_serial in delete_request.devices_serials:
                expected_calls.append(
                    (
                        f"{iota_proxy.iota_url}/iot/devices/{device_serial}",
                        {
                            "headers": {
                                "fiware-service": iota_proxy.tenant,
                                "fiware-servicepath": scopeDefault,
                            }
                        },
                    )
                )

            for i, call_arg in enumerate(mock_session_delete.call_args_list):
                assert call_arg.args[0] == expected_calls[i][0]
                assert (
                    call_arg.kwargs["headers"] == expected_calls[i][1]["headers"]
                )
                
        if not delete_request.devices_serials:
            mock_session_delete.assert_not_called()
