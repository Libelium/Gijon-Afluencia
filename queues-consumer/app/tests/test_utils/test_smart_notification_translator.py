from utils.ngsi.cb_notification_translator.ngsi_ld_notification_translator import NgsiLdNormalizedNotificationTranslator
from schemas.context_broker_notification_schema import ContextBrokerNotification
from utils.ngsi.cb_notification_translator.smart_notification_translator import (
    SmartNotificationTranslator,
    NotificationType,
)
import pytest


@pytest.fixture
def smart_notification_translator():
    return SmartNotificationTranslator(default_translator=NgsiLdNormalizedNotificationTranslator)


class TestSmartNotificationTranslator:

    @pytest.mark.parametrize(
        ("notification", "expected"),
        [
            (
                ContextBrokerNotification(
                    headers={
                        "ngsild-tenant": "test_tenant",
                        "ngsiv2-attrsformat": "normalized",
                    },
                    body={},
                ),
                NotificationType.NGSI_LD_NORMALIZED,
            ),
            (
                ContextBrokerNotification(
                    headers={
                        "ngsild-tenant": "test_tenant",
                        "ngsiv2-attrsformat": "not-normalized",
                    },
                    body={},
                ),
                NotificationType.UNKNOWN,
            ),
            (
                ContextBrokerNotification(
                    headers={
                        "ngsild-tenant": "test_tenant",
                    },
                    body={},
                ),
                NotificationType.UNKNOWN,
            ),
            (
                ContextBrokerNotification(
                    headers={
                        "ngsiv2-attrsformat": "normalized",
                    },
                    body={},
                ),
                NotificationType.UNKNOWN,
            ),
            (
                ContextBrokerNotification(
                    headers={},
                    body={},
                ),
                NotificationType.UNKNOWN,
            ),
            (
                ContextBrokerNotification(
                    headers={
                        "fiware-service": "test_service",
                        "fiware-servicepath": "test_path",
                        "ngsiv2-attrsformat": "normalized",
                    },
                    body={},
                ),
                NotificationType.NGSI_V2_NORMALIZED,
            ),
            (
                ContextBrokerNotification(
                    headers={
                        "fiware-service": "test_service",
                        "ngsiv2-attrsformat": "normalized",
                    },
                    body={},
                ),
                NotificationType.UNKNOWN,
            ),
            (
                ContextBrokerNotification(
                    headers={
                        "fiware-servicepath": "test_path",
                        "fiware-service": "test_service",
                        "ngsiv2-attrsformat": "normalized",
                    },
                    body={},
                ),
                NotificationType.NGSI_V2_NORMALIZED
            ),
            (
                ContextBrokerNotification(
                    headers={
                        "fiware-servicepath": "test_path",
                        "ngsiv2-attrsformat": "normalized",
                    },
                    body={},
                ),
                NotificationType.UNKNOWN
            )
        ]
    )
    def test_smart_notification_get_notification_type(
        self,
        notification: ContextBrokerNotification,
        expected: NotificationType,
        smart_notification_translator: SmartNotificationTranslator,
    ):
        assert smart_notification_translator._SmartNotificationTranslator__get_notification_type(
            notification
        ) == expected
