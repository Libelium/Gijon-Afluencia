import pydantic
import pytest

from aether_pylib.context_broker.ngsi_ld_subscription import (
    NgsiLdSubscription,
)


class TestContextBrokerSchemas:
    @pytest.mark.parametrize(
        ("subscription_dict", "valid"),
        [
            (
                {
                    "id": "urn:ngsi-ld:Subscription:platform:mainSub",
                    "type": "Subscription",
                    "subscriptionName": "TROE-DeviceMeasurement-Timestream",
                    "description": "Subscription for timestream historial context extractor",
                    "entities": [{"type": "Device"}],
                    "notification": {
                        "format": "normalized",
                        "sysAttrs": True,
                        "showChanges": True,
                        "endpoint": {
                            "uri": "http://notification-endpoint.example:8888/hello-world",
                            "accept": "application/json",
                        },
                    },
                },
                True,
            ),
            (
                # without id
                {
                    "type": "Subscription",
                    "subscriptionName": "TROE-DeviceMeasurement-Timestream",
                    "description": "Subscription for timestream historial context extractor",
                    "entities": [{"type": "Device"}],
                    "notification": {
                        "format": "normalized",
                        "sysAttrs": True,
                        "showChanges": True,
                        "endpoint": {
                            "uri": "http://notification-endpoint.example:8888/hello-world",
                            "accept": "application/json",
                        },
                    },
                },
                False,
            ),
            (
                # without endpoint
                {
                    "id": "urn:ngsi-ld:Subscription:platform:mainSub",
                    "type": "Subscription",
                    "subscriptionName": "TROE-DeviceMeasurement-Timestream",
                    "description": "Subscription for timestream historial context extractor",
                    "entities": [{"type": "Device"}],
                    "notification": {
                        "format": "normalized",
                        "sysAttrs": True,
                        "showChanges": True,
                    },
                },
                False,
            ),
            (
                # without notification
                {
                    "id": "urn:ngsi-ld:Subscription:platform:mainSub",
                    "type": "Subscription",
                    "subscriptionName": "TROE-DeviceMeasurement-Timestream",
                    "description": "Subscription for timestream historial context extractor",
                    "entities": [{"type": "Device"}],
                },
                False,
            ),
            (
                # without entities
                {
                    "id": "urn:ngsi-ld:Subscription:platform:mainSub",
                    "type": "Subscription",
                    "subscriptionName": "TROE-DeviceMeasurement-Timestream",
                    "description": "Subscription for timestream historial context extractor",
                    "notification": {
                        "format": "normalized",
                        "sysAttrs": True,
                        "showChanges": True,
                        "endpoint": {
                            "uri": "http://notification-endpoint.example:8888/hello-world",
                            "accept": "application/json",
                        },
                    },
                },
                False,
            ),
            (
                # with extra params (ngsild specified ones)
                {
                    "id": "urn:ngsi-ld:Subscription:platform:mainSub",
                    "type": "Subscription",
                    "subscriptionName": "TROE-DeviceMeasurement-Timestream",
                    "description": "Subscription for timestream historial context extractor",
                    "entities": [{"type": "Device"}],
                    "watchedAttributes": ["temperature"],
                    "notification": {
                        "format": "normalized",
                        "sysAttrs": True,
                        "showChanges": True,
                        "endpoint": {
                            "uri": "http://notification-endpoint.example:8888/hello-world",
                            "accept": "application/json",
                            "cooldown": 10,
                        },
                    },
                },
                True,
            ),
        ],
    )
    def test_ngsi_ld_subscription(self, subscription_dict: dict, valid: bool):
        try:
            subscription = NgsiLdSubscription(**subscription_dict)
            assert valid

        except Exception as e:
            assert not valid
