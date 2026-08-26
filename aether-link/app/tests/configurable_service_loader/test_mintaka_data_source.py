import os
import pytest
from unittest import mock

from app.core.config.configurable_service_loader import ConfigurableServiceLoader
from app.core.time_series.data_sources.mintaka.mintaka_data_source import (
    MintakaDataSource,
)


@pytest.fixture
def configurable_service_loader():
    return ConfigurableServiceLoader({"mintaka": MintakaDataSource})


class TestMintakaDataSourceLoading:
    @pytest.mark.parametrize(
        ("params", "valid"),
        [
            (
                {
                    "MINTAKA_SERVICE_URL": "http://mintaka:8080",
                    "DEFAULT_TENANT": "gijon",
                    "CONTEXT_URL": "http://orion-ld:1026",
                },
                True,
            ),
            (
                {
                    "MINTAKA_SERVICE_URL": "http://mintaka:8080",
                    "CONTEXT_URL": "http://orion-ld:1026",
                    "DEFAULT_ENTITY_PAGE_SIZE": "100",
                },
                False,
            ),
            (
                {
                    "MINTAKA_SERVICE_URL": "http://mintaka:8080",
                    "DEFAULT_TENANT": "gijon",
                    "DEFAULT_ENTITY_PAGE_SIZE": "100",
                },
                False,
            ),
        ],
    )
    def test_data_source_params(
        self,
        params: dict,
        valid: bool,
        configurable_service_loader: ConfigurableServiceLoader,
    ):
        mocker = mock.patch.dict(os.environ, params)
        mocker.start()

        try:
            data_source = configurable_service_loader.load("mintaka")
            assert valid
        except Exception as e:
            assert not valid
