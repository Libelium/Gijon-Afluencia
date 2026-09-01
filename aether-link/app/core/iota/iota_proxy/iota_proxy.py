from abc import abstractmethod
from typing import List

from app.core.configurable_service.configurable_service import ConfigurableService
from aether_pylib.iota.iota_provision_payload import (
    DeviceProvisionPayload,
    ServiceProvisionPayload,
)


class IOTAProxy(ConfigurableService):
    """Generic IOTA proxy"""

    @abstractmethod
    def get_services(
        self,
        entity_type: str | None,
        device_type_code: str | None,
        tenant: str,
        scope: str,
    ):
        """Get the services from the IOTA, optionally filtered"""
        pass

    @abstractmethod
    def provision_service(
        self, service: ServiceProvisionPayload, tenant: str, scope: str
    ):
        """Provision a new service in the IOTA"""

    @abstractmethod
    def provision_device(
        self, payload: DeviceProvisionPayload, tenant: str, scope: str
    ) -> bool:
        """Provision a new device in the IOTA"""
        pass
