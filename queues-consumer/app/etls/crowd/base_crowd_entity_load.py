import math
from typing import Tuple

from sqlalchemy.orm import Session

from config.logging import appLogging as logging
import helpers.aether_link.aether_link_helper as aether_link_helper
from models.preferences_model import PreferenceType
import models.crud.crud_tenant_scope as crud_tenant_scope
import models.crud.crud_preferences as crud_preferences
from helpers.iota import iota_helper


class BaseCrowdEntityLoad:
    """Shared IoT-Agent publishing pipeline for the crowd ETL loaders.

    The concrete loaders (ProcessVisitorsLoad, CrowdFlowsMunicipalityLoad) provide the
    transform-output attributes (``result``, ``entities``, ``start_date``, ``end_date``,
    ``mode``, ``user_id``, ``main_db``) through their own ``__init__`` and implement
    ``_process_to_fiware`` / ``_generate_entity_payload`` with the fields specific to
    each entity model. Everything else - resolving the user's apikey/resource through
    the Aether Link and posting each entity to the IoT Agent - is identical between them
    and lives here.
    """

    def _get_datamodel_apikey_resource(
        self, tenant: str, scope: str, datamodel: str
    ) -> Tuple[str, str]:
        """
        As it says, just get the apikey for a data model from a given tenant and scope,
        using the Aether Link.
        returns a tuple (apikey, resource)
        """

        services = aether_link_helper.get_iota_services(tenant, scope, datamodel)

        if not services or len(services) == 0:
            raise Exception(
                f"Error getting service for params tenant: {tenant}, scope: {scope}, datamodel: {datamodel}"
            )

        if len(services) > 1:
            logging.warning(
                f"More than one iota service found for params tenant: "
                f"{tenant}, scope: {scope}, datamodel: {datamodel}"
            )

        service = services[0]
        apikey = service.get("apikey")
        resource = service.get("resource")

        if not apikey:
            raise Exception(
                f"Error getting apikey for params tenant: {tenant}, scope: {scope}, datamodel: {datamodel}"
            )

        if not resource:
            raise Exception(
                f"Error getting resource for params tenant: {tenant}, scope: {scope}, datamodel: {datamodel}"
            )

        return apikey, resource

    def _get_user_apikey_resource(
        self, user_id: int, datamodel: str, main_db: Session
    ) -> Tuple[str, str]:
        """
        Gets the apikey of the user for the given data model
        returns a tuple (apikey, resource)
        """

        scope_id = crud_preferences.get_user_preference(
            user_id=user_id,
            preference_name=PreferenceType.PLATFORM_DATA_SCOPE,
            db=main_db,
        )

        if not scope_id:
            raise Exception(
                f"User {user_id} has no scope preference, cannot get apikey"
            )

        tenant, scope = crud_tenant_scope.get_tenant_scope(scope_id, main_db)

        if not scope:
            raise Exception(
                f"Scope {scope_id} not found in the database, cannot get apikey"
            )

        return self._get_datamodel_apikey_resource(
            tenant=tenant, scope=scope, datamodel=datamodel
        )

    def _send_to_iota(self):
        """
        Function to send the processed data to IOTA
        """
        try:
            apikey, resource = self._get_user_apikey_resource(
                user_id=self.user_id,
                datamodel="CrowdFlowEventETL",
                main_db=self.main_db,
            )

            for data in self.iota_payload:
                try:
                    logging.info(
                        f"Sending data to iot agent for entity {data['entityId']}"
                    )

                    entity_id = data["entityId"]

                    payload = {
                        k: v
                        for k, v in data.items()
                        if (k != "entityId")
                        and (v is not None)
                        and (not ((isinstance(v, float) and math.isnan(v))))
                    }

                    # urn:ngsi-ld:Datamodel:id
                    iota_helper.publish_data(
                        id=entity_id,
                        apikey=apikey,
                        resource=resource,
                        body=payload,
                    )

                except Exception as e:
                    logging.error(f"Error sending data to iot agent: {e}")

        except Exception as e:
            logging.error(f"Error getting apikey and resource: {e}")
            return

    def _get_entity_id_from_urn(self, urn: str) -> str:
        """
        Function to get the entity id from the urn
        """
        return urn.split(":")[-1]

    def load(self):
        if not self.result.empty:
            if self.mode == "tourism":
                self._process_to_fiware(self.result)
                self._send_to_iota()

            else:
                logging.error(f"Mode not supported: {self.mode}")

                return False
        else:
            logging.error("No data to upload")

        return True
