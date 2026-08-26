import os
from typing import Dict

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

from app.core.config.configurable_service_loader import ConfigurableServiceLoader
from app.core.config.logging import appLogging as logging
from app.core.configurable_service.configurable_service import ConfigurableService
from app.core.context_broker.context_broker_proxy.context_broker_proxy import (
    ContextBrokerProxy,
)
from app.core.context_broker.context_broker_proxy.orion_ld_proxy.orion_ld_proxy import (
    OrionLdProxy,
)
from app.core.context_broker.context_broker_proxy.orion_v2_proxy.orion_v2_proxy import (
    OrionV2Proxy,
)
from app.core.iota.iota_proxy.iota_json_proxy.iota_json_ld_proxy import IOTAJsonLdProxy
from app.core.iota.iota_proxy.iota_json_proxy.iota_json_v2_proxy import IOTAJsonV2Proxy
from app.core.time_series.data_sources.data_source import DataSource
from app.core.time_series.data_sources.timescale.timescale_data_source import (
    TimescaleDatasource,
)
from app.core.time_series.data_sources.mintaka.mintaka_data_source import (
    MintakaDataSource,
)
from app.core.time_series.data_sources.orion_ld_timescale.orion_ld_timescale_data_source import (
    OrionLDTimescaleDataSource,
)
from app.core.time_series.data_sources.quantum_leap.quantum_leap_data_source import (
    QuantumLeapDataSource,
)

# Load the env file
load_dotenv()


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    ENABLE_SWAGGER: bool = os.getenv("ENABLE_SWAGGER", False)

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "ERROR")
    QUEUES_CONSUMER_API: str = os.getenv("QUEUES_CONSUMER_API", "")
    DATA_SOURCE_TYPE: str = os.getenv("DATA_SOURCE_TYPE", "")
    CONTEXT_BROKER_TYPE: str = os.getenv("CONTEXT_BROKER_TYPE", "")
    IOTA_TYPE: str = os.getenv("IOTA_TYPE", "")
    DEFAULT_TENANT: str = os.getenv("DEFAULT_TENANT", "")
    DEFAULT_SCOPE: str = os.getenv("DEFAULT_SCOPE", "/")
    AVAILABLE_SERVICES: dict = {
        "mintaka": MintakaDataSource,
        "orionld": OrionLdProxy,
        "orionv2": OrionV2Proxy,
        "quantumleap": QuantumLeapDataSource,
        "iotajsonLd": IOTAJsonLdProxy,
        "iotajsonV2": IOTAJsonV2Proxy,
        "orion_ld_timescale": OrionLDTimescaleDataSource,
        "timescale": TimescaleDatasource,
    }

    class Config:
        case_sensitive = True


settings = Settings()
time_series_data_source: DataSource = None
context_broker_proxy: ContextBrokerProxy = None
iota_proxy = None

service_loader = ConfigurableServiceLoader(settings.AVAILABLE_SERVICES)

# If this fails, the app will not work but you will still
# be able to start the container
try:

    time_series_data_source = service_loader.load(settings.DATA_SOURCE_TYPE)

except Exception as e:
    logging.error(f"Error loading time series data source: {e}")

try:
    context_broker_proxy = service_loader.load(settings.CONTEXT_BROKER_TYPE)
except Exception as e:
    logging.error(f"Error loading context broker proxy: {e}")

try:
    iota_proxy = service_loader.load(settings.IOTA_TYPE)
except Exception as e:
    logging.error(f"Error loading IOTA proxy: {e}")

# To automatically check the health of the services and log the errors
healthchecks: Dict[str, ConfigurableService] = {
    "time_series_data_source": time_series_data_source,
    "context_broker_proxy": context_broker_proxy,
    "iota_proxy": iota_proxy,
}
