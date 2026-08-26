import os
import pytest
from unittest import mock

from app.core.config.configurable_service_loader import ConfigurableServiceLoader
from app.core.context_broker.context_broker_proxy.orion_ld_proxy.orion_ld_proxy import (
    OrionLdProxy,
)


@pytest.fixture
def configurable_service_loader():
    return ConfigurableServiceLoader({"orionld": OrionLdProxy})


class TestOrionLdProxy:
    @pytest.mark.parametrize(
        ("params", "valid"),
        [
            (
                {
                    "ORION_LD_SERVICE": "http://orion-ld:1026",
                    "DEFAULT_TENANT": "gijon",
                    "CONTEXT_URL": "http://context-server/context.jsonld",
                    "PLATFORM_SUBSCRIPTION_CONSUMER": "http://platform:8080",
                    "PLATFORM_SUBSCRIPTION_URN": "urn:ngsi-ld:Subscription:platform:main"
                },
                True,
            ),
            (
                {
                    "ORION_LD_SERVICE": "http://orion-ld:1026",
                    "DEFAULT_TENANT": "gijon",
                    "CONTEXT_URL": "http://context-server/context.jsonld",
                    "PLATFORM_SUBSCRIPTION_CONSUMER": "http://platform:8080",
                },
                True,
            ),
            (
                {
                    "ORION_LD_SERVICE": "http://orion-ld:1026",
                    "CONTEXT_URL": "http://context-server/context.jsonld",
                    "PLATFORM_SUBSCRIPTION_CONSUMER": "http://platform:8080",
                    "PLATFORM_SUBSCRIPTION_URN": "urn:ngsi-ld:Subscription:platform:main"
                },
                False,
            ),
            (
                {
                    "ORION_LD_SERVICE": "http://orion-ld:1026",
                    "DEFAULT_TENANT": "gijon",
                    "PLATFORM_SUBSCRIPTION_CONSUMER": "http://platform:8080",
                    "PLATFORM_SUBSCRIPTION_URN": "urn:ngsi-ld:Subscription:platform:main"
                },
                False,
            ),
            (
                {
                    "ORION_LD_SERVICE": "http://orion-ld:1026",
                    "DEFAULT_TENANT": "gijon",
                    "CONTEXT_URL": "http://context-server/context.jsonld",
                    "PLATFORM_SUBSCRIPTION_URN": "urn:ngsi-ld:Subscription:platform:main"
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
            data_source = configurable_service_loader.load("orionld")
            assert valid
        except Exception as e:
            assert not valid
