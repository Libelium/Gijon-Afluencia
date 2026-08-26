import datetime
from enum import Enum
from utils.ngsi.cb_notification_translator.ngsi_v2_notification_translator import (
    NgsiV2NormalizedNotificationTranslator,
)
from schemas.entity_data_notification import DataNotification
from utils.ngsi.cb_notification_translator.ngsi_ld_notification_translator import (
    NgsiLdNormalizedNotificationTranslator,
)
from schemas.context_broker_notification_schema import ContextBrokerNotification
from utils.ngsi.cb_notification_translator.cb_notification_translator import (
    CBNotificationTranslator,
)


class NotificationType(str, Enum):
    NGSI_LD_NORMALIZED = "NGSI_LD_NORMALIZED"
    NGSI_V2_NORMALIZED = "NGSI_V2_NORMALIZED"
    UNKNOWN = "UNKNOWN"


class SmartNotificationTranslator(CBNotificationTranslator):
    """
    Smart translator that is able to detect the notification type and
    translate it using the appropriate translator.
    """

    def __init__(self, default_translator=None):
        """
        Initialize the translator type map
        """

        self.__translator_for_type = {
            NotificationType.NGSI_LD_NORMALIZED: NgsiLdNormalizedNotificationTranslator,
            NotificationType.NGSI_V2_NORMALIZED: NgsiV2NormalizedNotificationTranslator,
            # For unknown types, use the NgsiLdNormalizedNotificationTranslator, as it is the most generic one for now
            NotificationType.UNKNOWN: default_translator,
        }

    def __get_notification_type(
        self, notification: ContextBrokerNotification
    ) -> NotificationType:
        """
        Get the notification type.
        """

        if self.__is_ngsi_v2_normalized(notification):
            return NotificationType.NGSI_V2_NORMALIZED

        if self.__is_ngsi_ld_normalized(notification):
            return NotificationType.NGSI_LD_NORMALIZED

        return NotificationType.UNKNOWN

    def __is_ngsi_ld_normalized(self, notification: ContextBrokerNotification) -> bool:
        """
        Returns true if the notification is in NGSI-LD normalized format.
        For this, it should have the following headers:
        - ngsild-tenant
        - ngsiv2-attrsformat = normalized
        """

        if notification.headers is None:
            return False

        tenant = notification.headers.get("ngsild-tenant", None)
        format = notification.headers.get("ngsiv2-attrsformat", None)
        if tenant is None or format != "normalized":
            return False

        return True

    def __is_ngsi_v2_normalized(self, notification: ContextBrokerNotification) -> bool:
        """
        Returns true if the notification is in NGSI-V2 normalized format.
        For this, it should have the following headers:
        - ngsiv2-attrsformat = normalized
        """

        if notification.headers is None:
            return False

        format = notification.headers.get("ngsiv2-attrsformat", None)
        if format != "normalized":
            return False
        service = notification.headers.get("fiware-service", None)
        path = notification.headers.get("fiware-servicepath", None)
        if service is None or path is None:
            return False

        return True

    def translate(
        self, notification: ContextBrokerNotification
    ) -> DataNotification:
        """
        Translates the notification using the appropriate translator,
        according to self.__get_notification_type.
        """

        notification_type = self.__get_notification_type(notification)
        translator: CBNotificationTranslator = self.__translator_for_type[
            notification_type
        ]()

        return translator.translate(notification)

    def translate_entity(
        self, entity: dict, default_timestamp: datetime, tenant: str, scope: str
    ) -> DataNotification:
        """
        Translates a single NGSI-LD normalized entity into a Platform data notification.
        WARNING: It does not fill the db_id.
        It is not possible to distinguish the entity type from the entity itself, we need 
        the headers for that, so for now we are using the default translator for unknown types.
        """

        translator: CBNotificationTranslator = self.__translator_for_type[
            NotificationType.UNKNOWN
        ]()
        
        return translator.translate_entity(entity, default_timestamp, tenant, scope)
