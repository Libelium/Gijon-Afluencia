from fastapi import HTTPException
from app.core.iota.iota_proxy.iota_proxy import IOTAProxy
from aether_pylib.iota.iota_provision_payload import (
    DeviceProvisionPayload,
    ServiceProvisionPayload,
)
from aether_pylib.iota.delete_devices_request import DeleteDevicesRequest
from aether_pylib.iota.delete_devices_result import (
    DeviceBatchOperationError,
    DeleteDevicesResult,
)
from app.core.config.logging import appLogging as logging
import requests


class IOTAJsonLdProxy(IOTAProxy):
    """Generic IOTA proxy"""

    def __init__(self, **kwargs):
        self.iota_url = kwargs["IOTA_JSON_URL"]
        self.tenant = kwargs["DEFAULT_TENANT"]
        if self.iota_url is None:
            raise Exception(
                "Missing required parameters.\n" + str(self.params_description())
            )

    def params_description() -> dict:
        return {
            "IOTA_JSON_URL": {
                "description": "iota json north url",
                "type": str,
                "required": True,
                "default": "",
            },
            "DEFAULT_TENANT": {
                "description": "NGSI LD tenant name",
                "type": str,
                "required": True,
                "default": "",
            },
        }

    def health_check(self) -> bool:
        """
        Return true if the service is ready to be used, throw an exception otherwise
        """
        session = requests.Session()
        response = session.get(self.iota_url + "/iot/about", timeout=5)
        if response.status_code != 200:
            raise Exception(f"IOTA JSON service is not ready: {response.text}")

        return True

    def get_services(self, entity_type: str | None, device_type_code: str | None, tenant: str, scope: str):
        """Get a service from the IOTA"""
        try:
            self.tenant = tenant if tenant else self.tenant
            headers = {"fiware-service": self.tenant, "fiware-servicepath": scope}
            res = requests.get(self.iota_url + "/iot/services", headers=headers)
            services = res.json().get("services", [])
            if entity_type is None:
                return services

            req_services = [
                service for service in services if service["entity_type"] == entity_type 
            ]
            
            if device_type_code:
                req_services = [
                    service for service in services if service["internal_attributes"][0]["device_type_code"] == device_type_code 
                ]

            if not req_services:
                raise HTTPException(status_code=404, detail="Service not found")
            return req_services

        except Exception as e:
            logging.error(f"Error getting services: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    def provision_service(
        self, service: ServiceProvisionPayload, tenant: str, scope: str
    ):
        try:
            self.tenant = tenant if tenant else self.tenant
            headers = {"fiware-service": self.tenant, "fiware-servicepath": scope}
            return requests.post(
                self.iota_url + "/iot/services",
                headers=headers,
                json=service.model_dump(),
            )
        except Exception as e:
            logging.error(f"Error provisioning device: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    def provision_device(
        self, payload: DeviceProvisionPayload, tenant: str, scope: str
    ) -> DeviceProvisionPayload:
        """Provision a new device in the IOTA"""
        try:
            self.tenant = tenant if tenant else self.tenant
            headers = {"fiware-service": self.tenant, "fiware-servicepath": scope}
            requests.post(
                self.iota_url + "/iot/devices",
                headers=headers,
                json=payload.model_dump(exclude_none=True),
            )
        except Exception as e:
            logging.error(f"Error provisioning device: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    def delete_devices(self, devices: DeleteDevicesRequest, tenant: str, scope: str):
        """Delete devices from the IOTA"""
        session = requests.Session()
        deleted_devices = []
        errors = []
        try:
            for device in devices.devices_serials:
                response = session.delete(
                    f"{self.iota_url}/iot/devices/{device}",
                    headers={"fiware-service": tenant, "fiware-servicepath": scope},
                )
                if response.status_code == 204:
                    deleted_devices.append(device)
                elif response.status_code == 404:
                    errors.append(
                        DeviceBatchOperationError(
                            id=device,
                            error={"message": "Device not found", "status": 404},
                        )
                    )
                    logging.warning(f"Device {device} not found for delete.")
                else:
                    error_detail = (
                        response.text or f"Status Code: {response.status_code}"
                    )
                    errors.append(
                        DeviceBatchOperationError(
                            id=device,
                            error={
                                "message": f"Error deleting device: {error_detail}",
                                "status": response.status_code,
                            },
                        )
                    )
                    logging.error(
                        f"Error deleting device {device}: {response.status_code} - {response.text}"
                    )

        except Exception as e:
            errors.append(
                DeviceBatchOperationError(
                    id=device,
                    error={
                        "message": f"Network or connection error: {str(e)}",
                        "status": 500,
                    },
                )
            )
            logging.error(f"Error deleting devices: {e}")

        session.close()
        return DeleteDevicesResult(devices=deleted_devices, errors=errors)
