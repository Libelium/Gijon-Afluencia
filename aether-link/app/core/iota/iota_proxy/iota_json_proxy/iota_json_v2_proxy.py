from app.core.iota.iota_proxy.iota_json_proxy.iota_json_ld_proxy import IOTAJsonLdProxy
from app.core.iota.iota_proxy.translation.ld_2_v2_translation import bulk_ld_2_v2
from aether_pylib.iota.iota_provision_payload import (
    DeviceProvisionPayload,
)


class IOTAJsonV2Proxy(IOTAJsonLdProxy):
    """
    This IOTA JSON proxy is the same as the IOTA JSON LD proxy
    but with the difference that it is using the NGSI-V2
    format instead of NGSI-LD.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def provision_device(
        self, payload: DeviceProvisionPayload, tenant: str, scope: str
    ):
        """
        Provision a device in the IOTA, translating the DeviceProvisionPayload
        to the NGSI-V2 format.
        """

        payload = bulk_ld_2_v2(payload)

        return super().provision_device(payload, tenant, scope)
