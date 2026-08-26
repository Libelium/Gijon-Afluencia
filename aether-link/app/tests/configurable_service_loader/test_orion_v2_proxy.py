import os
from app.core.context_broker.context_broker_proxy.orion_v2_proxy.orion_v2_proxy import (
    OrionV2Proxy,
)
import pytest
from unittest import mock

from app.core.config.configurable_service_loader import ConfigurableServiceLoader


@pytest.fixture
def configurable_service_loader():
    return ConfigurableServiceLoader({"orionv2": OrionV2Proxy})


class TestOrionLdProxy:
    @pytest.mark.parametrize(
        ("params", "valid"),
        [
            (
                {
                    "ORION_V2_SERVICE": "http://orion-ld:1026",
                    "DEFAULT_TENANT": "gijon",
                    "PLATFORM_SUBSCRIPTION_CONSUMER": "http://platform:8080",
                    "PLATFORM_SUBSCRIPTION_ID_TEXT": "[--platform]",
                },
                True,
            ),
            (
                {
                    "ORION_V2_SERVICE": "http://orion-ld:1026",
                    "DEFAULT_TENANT": "gijon",
                    "PLATFORM_SUBSCRIPTION_CONSUMER": "http://platform:8080",
                },
                True,
            ),
            (
                {
                    "DEFAULT_TENANT": "gijon",
                    "PLATFORM_SUBSCRIPTION_CONSUMER": "http://platform:8080",
                    "PLATFORM_SUBSCRIPTION_ID_TEXT": "[--platform]",
                },
                False
            ),
            (
                {
                    "ORION_V2_SERVICE": "http://orion-ld:1026",
                    "PLATFORM_SUBSCRIPTION_CONSUMER": "http://platform:8080",
                    "PLATFORM_SUBSCRIPTION_ID_TEXT": "[--platform]",
                },
                False,
            ),
            (
                {
                    "ORION_V2_SERVICE": "http://orion-ld:1026",
                    "DEFAULT_TENANT": "gijon",
                    "PLATFORM_SUBSCRIPTION_ID_TEXT": "[--platform]",
                },
                False,
            ),
        ],
    )
    def test_data_source_params(
        self,
        params: str,
        valid: bool,
        configurable_service_loader: ConfigurableServiceLoader,
    ):
        mocker = mock.patch.dict(os.environ, params)
        mocker.start()

        try:
            _ = configurable_service_loader.load("orionv2")
            assert valid
        except Exception as e:
            assert not valid
