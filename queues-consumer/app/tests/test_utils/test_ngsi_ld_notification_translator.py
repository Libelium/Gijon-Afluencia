from schemas.context_broker_notification_schema import ContextBrokerNotification
import pytest
from schemas.entity_data_notification import (
    DataNotification,
    EntityAttr,
    EntityAttrType,
    EntityDataNotification,
)
from utils.ngsi.cb_notification_translator.ngsi_ld_notification_translator import (
    NgsiLdNormalizedNotificationTranslator,
)
from datetime import datetime
import dateutil.parser


@pytest.fixture(scope="class")
def translator():
    return NgsiLdNormalizedNotificationTranslator()


def timestamp_from(date_str: str):
    # witout timezone
    date = dateutil.parser.parse(date_str)
    return date.timestamp()


def date_from(date_str: str):
    # witout timezone
    date = dateutil.parser.parse(date_str)
    return date


class TestNgsiLdNotificationTranslator:

    @pytest.mark.parametrize(
        (
            "attr_name",
            "attr_value",
            "comand_cache",
            "default_timestamp",
            "expected_result",
            "expected_command_cache",
        ),
        [
            (
                "temperature",
                {
                    "type": "Property",
                    "value": 32,
                    "unitCode": "C",
                    "observedAt": "2024-01-01T00:00:00.000Z",
                },
                {},
                date_from("2024-01-02T00:00:00.000Z"),
                EntityAttr(
                    name="temperature",
                    value=32,
                    type=EntityAttrType.PROPERTY,
                    timestamp=timestamp_from("2024-01-01T00:00:00"),
                    units="C",
                ),
                {},
            ),
            (
                "temperature",
                {
                    "type": "Property",
                    "value": 32,
                    "unitCode": "C",
                },
                {},
                date_from("2024-01-02T00:00:00.000Z"),
                EntityAttr(
                    name="temperature",
                    value=32,
                    type=EntityAttrType.PROPERTY,
                    timestamp=timestamp_from("2024-01-02T00:00:00"),
                    units="C",
                    timestamp_override=True,
                ),
                {},
            ),
            (
                "temperature",
                {
                    "type": "Property",
                    "unitCode": "C",
                },
                {},
                date_from("2024-01-02T00:00:00.000Z"),
                None,
                {},
            ),
            (
                "temperature",
                {
                    "type": "Relationship",
                    "object": "urn:ngsi-ld:Building:farm001",
                    "observedAt": "2024-01-01T00:00:00.000Z",
                },
                {},
                date_from("2024-01-02T00:00:00.000Z"),
                EntityAttr(
                    name="temperature",
                    value="urn:ngsi-ld:Building:farm001",
                    type=EntityAttrType.RELATIONSHIP,
                    timestamp=timestamp_from("2024-01-01T00:00:00"),
                ),
                {},
            ),
            (
                "temperature",
                {
                    "type": "GeoProperty",
                    "observedAt": "2024-01-01T00:00:00.000Z",
                    "value": {
                        "type": "Point",
                        "coordinates": [1, 2],
                    },
                },
                {},
                date_from("2024-01-02T00:00:00.000Z"),
                EntityAttr(
                    name="temperature",
                    value={
                        "type": "Point",
                        "coordinates": [1, 2],
                    },
                    type=EntityAttrType.PROPERTY,
                    timestamp=timestamp_from("2024-01-01T00:00:00"),
                ),
                {},
            ),
            (
                "cmd_info",
                {
                    "type": "Property",
                    "observedAt": "2024-01-01T00:00:00.000Z",
                    "value": {
                        "@type": "commandResult",
                        "@value": 32,
                    },
                    "unitCode": "C",
                },
                {},
                date_from("2024-01-02T00:00:00.000Z"),
                None,
                {
                    "cmd": {
                        "info": 32,
                        "units": "C",
                        "info_timestamp": timestamp_from("2024-01-01T00:00:00"),
                    }
                },
            ),
            (
                "cmd_status",
                {
                    "type": "Property",
                    "observedAt": "2024-01-01T00:00:00.000Z",
                    "value": {
                        "@type": "commandStatus",
                        "@value": 32,
                    },
                    "unitCode": "C",
                },
                {},
                date_from("2024-01-02T00:00:00.000Z"),
                None,
                {
                    "cmd": {
                        "status": 32,
                        "units": "C",
                        "status_timestamp": timestamp_from("2024-01-01T00:00:00"),
                    }
                },
            ),
            (
                "cmd_status",
                {
                    "type": "Property",
                    "observedAt": "2024-01-01T00:00:00.000Z",
                    "value": {
                        "@type": "commandStatus",
                        "@value": 32,
                    },
                    "unitCode": "C",
                },
                {
                    "cmd": {
                        "info": 55,
                        "units": "C",
                        "info_timestamp": timestamp_from("2024-01-01T00:00:00"),
                    }
                },
                date_from("2024-01-02T00:00:00.000Z"),
                None,
                {
                    "cmd": {
                        "info": 55,
                        "status": 32,
                        "units": "C",
                        "status_timestamp": timestamp_from("2024-01-01T00:00:00"),
                        "info_timestamp": timestamp_from("2024-01-01T00:00:00"),
                    }
                },
            ),
        ],
    )
    def test_translate_entity_attribute(
        self,
        attr_name: str,
        attr_value: dict,
        comand_cache: dict,
        default_timestamp: datetime,
        expected_result: EntityAttr | None,
        expected_command_cache: dict,
        translator,
    ):
        result = translator._NgsiLdNormalizedNotificationTranslator__translate_entity_attribute(
            attr_name, attr_value, comand_cache, default_timestamp
        )
        assert result == expected_result
        assert comand_cache == expected_command_cache

    @pytest.mark.parametrize(
        ("normalized_entity", "default_timestamp", "expected_result"),
        [
            (
                {
                    "id": "urn:ngsi-ld:Device:filling001",
                    "type": "FillingLevelSensor",
                    "filling-old": {
                        "type": "Property",
                        "value": 0.50,
                        "unitCode": "C63",
                        "observedAt": "2020-12-08T16:26:12.000Z",
                    },
                    "filling": {
                        "type": "Property",
                        "value": 0.25,
                        "unitCode": "C62",
                        "observedAt": "2020-12-09T16:27:12.000Z",
                    },
                    "temperature": {
                        "type": "Property",
                        "value": 32,
                        "unitCode": "C",
                        "observedAt": "2020-12-09T16:28:12.000Z",
                    },
                    "controlledAsset": {
                        "type": "Relationship",
                        "object": "urn:ngsi-ld:Building:farm001",
                        "observedAt": "2020-12-09T16:29:12.000Z",
                    },
                },
                date_from("2024-01-01T00:00:00.000Z"),
                EntityDataNotification(
                    urn="urn:ngsi-ld:Device:filling001",
                    tenant="test",
                    notified_at=timestamp_from("2024-01-01T00:00:00"),
                    scope="/",
                    type="FillingLevelSensor",
                    db_id=None,
                    data=[
                        EntityAttr(
                            name="filling-old",
                            value=0.50,
                            type=EntityAttrType.PROPERTY,
                            timestamp=timestamp_from("2020-12-08T16:26:12"),
                            units="C63",
                        ),
                        EntityAttr(
                            name="filling",
                            value=0.25,
                            type=EntityAttrType.PROPERTY,
                            timestamp=timestamp_from("2020-12-09T16:27:12"),
                            units="C62",
                        ),
                        EntityAttr(
                            name="temperature",
                            value=32,
                            type=EntityAttrType.PROPERTY,
                            timestamp=timestamp_from("2020-12-09T16:28:12"),
                            units="C",
                        ),
                        EntityAttr(
                            name="controlledAsset",
                            value="urn:ngsi-ld:Building:farm001",
                            type=EntityAttrType.RELATIONSHIP,
                            timestamp=timestamp_from("2020-12-09T16:29:12"),
                        ),
                    ],
                ),
            ),
            (
                {
                    "id": "urn:ngsi-ld:Device:filling001",
                    "type": "FillingLevelSensor",
                    "filling-old": {
                        "type": "Property",
                        "value": 0.50,
                        "unitCode": "C63",
                        "observedAt": "2020-12-08T16:26:12.000Z",
                    },
                    "filling": {
                        "type": "Property",
                        "value": 0.25,
                        "unitCode": "C62",
                        "observedAt": "2020-12-09T16:27:12.000Z",
                    },
                    "temperature": {
                        "type": "Property",
                        "value": 32,
                        "unitCode": "C",
                        "observedAt": "2020-12-09T16:28:12.000Z",
                    },
                    "controlledAsset": {
                        "type": "Relationship",
                        "object": "urn:ngsi-ld:Building:farm001",
                        "observedAt": "2020-12-09T16:29:12.000Z",
                    },
                    "cmd_info": {
                        "type": "Property",
                        "observedAt": "2020-12-09T16:30:12.000Z",
                        "value": {
                            "@type": "commandResult",
                            "@value": 32,
                        },
                    },
                },
                date_from("2024-01-01T00:00:00.000Z"),
                EntityDataNotification(
                    urn="urn:ngsi-ld:Device:filling001",
                    tenant="test",
                    notified_at=timestamp_from("2024-01-01T00:00:00"),
                    scope="/",
                    type="FillingLevelSensor",
                    db_id=None,
                    data=[
                        EntityAttr(
                            name="filling-old",
                            value=0.50,
                            type=EntityAttrType.PROPERTY,
                            timestamp=timestamp_from("2020-12-08T16:26:12"),
                            units="C63",
                        ),
                        EntityAttr(
                            name="filling",
                            value=0.25,
                            type=EntityAttrType.PROPERTY,
                            timestamp=timestamp_from("2020-12-09T16:27:12"),
                            units="C62",
                        ),
                        EntityAttr(
                            name="temperature",
                            value=32,
                            type=EntityAttrType.PROPERTY,
                            timestamp=timestamp_from("2020-12-09T16:28:12"),
                            units="C",
                        ),
                        EntityAttr(
                            name="controlledAsset",
                            value="urn:ngsi-ld:Building:farm001",
                            type=EntityAttrType.RELATIONSHIP,
                            timestamp=timestamp_from("2020-12-09T16:29:12"),
                        ),
                        EntityAttr(
                            name="cmd",
                            value={
                                "info": 32,
                                "info_timestamp": timestamp_from("2020-12-09T16:30:12"),
                            },
                            type=EntityAttrType.COMMAND,
                            timestamp=timestamp_from("2020-12-09T16:30:12"),
                            units=None,
                        ),
                    ],
                ),
            ),
            (
                {
                    "id": "urn:ngsi-ld:Device:filling001",
                    "type": "FillingLevelSensor",
                    "filling-old": {
                        "type": "Property",
                        "value": 0.50,
                        "unitCode": "C63",
                        "observedAt": "2020-12-08T16:26:12.000Z",
                    },
                    "filling": {
                        "type": "Property",
                        "value": 0.25,
                        "unitCode": "C62",
                        "observedAt": "2020-12-09T16:27:12.000Z",
                    },
                    "temperature": {
                        "type": "Property",
                        "value": 32,
                        "unitCode": "C",
                        "observedAt": "2020-12-09T16:28:12.000Z",
                    },
                    "controlledAsset": {
                        "type": "Relationship",
                        "object": "urn:ngsi-ld:Building:farm001",
                        "observedAt": "2020-12-09T16:29:12.000Z",
                    },
                    "cmd_status": {
                        "type": "Property",
                        "observedAt": "2020-12-09T16:30:12.000Z",
                        "value": {
                            "@type": "commandStatus",
                            "@value": 32,
                        },
                    },
                },
                date_from("2024-01-01T00:00:00.000Z"),
                EntityDataNotification(
                    urn="urn:ngsi-ld:Device:filling001",
                    tenant="test",
                    scope="/",
                    notified_at=timestamp_from("2024-01-01T00:00:00"),
                    type="FillingLevelSensor",
                    db_id=None,
                    data=[
                        EntityAttr(
                            name="filling-old",
                            value=0.50,
                            type=EntityAttrType.PROPERTY,
                            timestamp=timestamp_from("2020-12-08T16:26:12"),
                            units="C63",
                        ),
                        EntityAttr(
                            name="filling",
                            value=0.25,
                            type=EntityAttrType.PROPERTY,
                            timestamp=timestamp_from("2020-12-09T16:27:12"),
                            units="C62",
                        ),
                        EntityAttr(
                            name="temperature",
                            value=32,
                            type=EntityAttrType.PROPERTY,
                            timestamp=timestamp_from("2020-12-09T16:28:12"),
                            units="C",
                        ),
                        EntityAttr(
                            name="controlledAsset",
                            value="urn:ngsi-ld:Building:farm001",
                            type=EntityAttrType.RELATIONSHIP,
                            timestamp=timestamp_from("2020-12-09T16:29:12"),
                        ),
                        EntityAttr(
                            name="cmd",
                            value={
                                "status": 32,
                                "status_timestamp": timestamp_from(
                                    "2020-12-09T16:30:12"
                                ),
                            },
                            type=EntityAttrType.COMMAND,
                            timestamp=timestamp_from("2020-12-09T16:30:12"),
                            units=None,
                        ),
                    ],
                ),
            ),
            (
                {
                    "id": "urn:ngsi-ld:Device:filling001",
                    "type": "FillingLevelSensor",
                    "filling-old": {
                        "type": "Property",
                        "value": 0.50,
                        "unitCode": "C63",
                        "observedAt": "2020-12-08T16:26:12.000Z",
                    },
                    "filling": {
                        "type": "Property",
                        "value": 0.25,
                        "unitCode": "C62",
                        "observedAt": "2020-12-09T16:27:12.000Z",
                    },
                    "temperature": {
                        "type": "Property",
                        "value": 32,
                        "unitCode": "C",
                        "observedAt": "2020-12-09T16:28:12.000Z",
                    },
                    "controlledAsset": {
                        "type": "Relationship",
                        "object": "urn:ngsi-ld:Building:farm001",
                        "observedAt": "2020-12-09T16:29:12.000Z",
                    },
                    "cmd_status": {
                        "type": "Property",
                        "observedAt": "2020-12-09T16:30:12.000Z",
                        "value": {
                            "@type": "commandStatus",
                            "@value": 32,
                        },
                    },
                    "cmd_info": {
                        "type": "Property",
                        "observedAt": "2020-12-10T16:30:12.000Z",
                        "value": {
                            "@type": "commandResult",
                            "@value": {
                                "status": 32,
                                "random": "value",
                            },
                        },
                    },
                },
                date_from("2024-01-01T00:00:00.000Z"),
                EntityDataNotification(
                    urn="urn:ngsi-ld:Device:filling001",
                    tenant="test",
                    notified_at=timestamp_from("2024-01-01T00:00:00"),
                    scope="/",
                    type="FillingLevelSensor",
                    db_id=None,
                    data=[
                        EntityAttr(
                            name="filling-old",
                            value=0.50,
                            type=EntityAttrType.PROPERTY,
                            timestamp=timestamp_from("2020-12-08T16:26:12"),
                            units="C63",
                        ),
                        EntityAttr(
                            name="filling",
                            value=0.25,
                            type=EntityAttrType.PROPERTY,
                            timestamp=timestamp_from("2020-12-09T16:27:12"),
                            units="C62",
                        ),
                        EntityAttr(
                            name="temperature",
                            value=32,
                            type=EntityAttrType.PROPERTY,
                            timestamp=timestamp_from("2020-12-09T16:28:12"),
                            units="C",
                        ),
                        EntityAttr(
                            name="controlledAsset",
                            value="urn:ngsi-ld:Building:farm001",
                            type=EntityAttrType.RELATIONSHIP,
                            timestamp=timestamp_from("2020-12-09T16:29:12"),
                        ),
                        EntityAttr(
                            name="cmd",
                            value={
                                "status": 32,
                                "status_timestamp": timestamp_from(
                                    "2020-12-09T16:30:12"
                                ),
                                "info": {
                                    "status": 32,
                                    "random": "value",
                                },
                                "info_timestamp": timestamp_from("2020-12-10T16:30:12"),
                            },
                            type=EntityAttrType.COMMAND,
                            timestamp=timestamp_from("2020-12-10T16:30:12"),
                            units=None,
                        ),
                    ],
                ),
            ),
            (
                {
                    "id": "urn:ngsi-ld:Device:filling001",
                    "filling-old": {
                        "type": "Property",
                        "value": 0.50,
                        "unitCode": "C63",
                        "observedAt": "2020-12-08T16:26:12.000Z",
                    },
                    "filling": {
                        "type": "Property",
                        "value": 0.25,
                        "unitCode": "C62",
                        "observedAt": "2020-12-09T16:27:12.000Z",
                    },
                },
                date_from("2024-01-01T00:00:00.000Z"),
                None,
            ),
            (
                {
                    "type": "FillingLevelSensor",
                    "filling-old": {
                        "type": "Property",
                        "value": 0.50,
                        "unitCode": "C63",
                        "observedAt": "2020-12-08T16:26:12.000Z",
                    },
                    "filling": {
                        "type": "Property",
                        "value": 0.25,
                        "unitCode": "C62",
                        "observedAt": "2020-12-09T16:27:12.000Z",
                    },
                },
                date_from("2024-01-01T00:00:00.000Z"),
                None,
            ),
        
            # Deleted entity notification - entity has deletedAt but no attributes
            (
                {
                    "id": "urn:ngsi-ld:Device:Device_4195",
                    "type": "https://uri.fiware.org/ns/dataModels#Device",
                    "deletedAt": "2025-12-19T08:36:25.218Z",
                },
                date_from("2025-12-19T08:36:25.218Z"),
                EntityDataNotification(
                    urn="urn:ngsi-ld:Device:Device_4195",
                    tenant="test",
                    notified_at=timestamp_from("2025-12-19T08:36:25.218Z"),
                    scope="/",
                    type="https://uri.fiware.org/ns/dataModels#Device",
                    db_id=None,
                    data=[],
                ),
            ),
        ],
    )
    def test_translate_entity(
        self,
        normalized_entity: dict,
        default_timestamp: datetime,
        expected_result: EntityDataNotification | None,
        translator,
    ):
        result = translator.translate_entity(
            normalized_entity, default_timestamp, "test", "/"
        )

        assert result == expected_result

    @pytest.mark.parametrize(
        ("notification", "expected_result"),
        [
            (
                ContextBrokerNotification(
                    headers={
                        "ngsild-tenant": "test",
                    },
                    body={
                        "id": "urn:ngsi-ld:Notification:6e19b6d2-cb01-11ee-bba4-02420a00000d",
                        "type": "Notification",
                        "subscriptionId": "urn:ngsi-ld:Subscription:6098eb9a-cb01-11ee-aa83-02420a00000d",
                        "notifiedAt": "2024-01-01T00:00:00.000Z",
                        "data": [
                            {
                                "id": "urn:ngsi-ld:Device:filling001",
                                "type": "FillingLevelSensor",
                                "filling-old": {
                                    "type": "Property",
                                    "value": 0.50,
                                    "unitCode": "C63",
                                    "observedAt": "2020-12-08T16:26:12.000Z",
                                },
                                "filling": {
                                    "type": "Property",
                                    "value": 0.25,
                                    "unitCode": "C62",
                                    "observedAt": "2020-12-09T16:27:12.000Z",
                                },
                                "temperature": {
                                    "type": "Property",
                                    "value": 32,
                                    "unitCode": "C",
                                    "observedAt": "2020-12-09T16:28:12.000Z",
                                },
                                "controlledAsset": {
                                    "type": "Relationship",
                                    "object": "urn:ngsi-ld:Building:farm001",
                                    "observedAt": "2020-12-09T16:29:12.000Z",
                                },
                                "cmd_status": {
                                    "type": "Property",
                                    "observedAt": "2020-12-09T16:30:12.000Z",
                                    "value": {
                                        "@type": "commandStatus",
                                        "@value": 32,
                                    },
                                },
                                "cmd_info": {
                                    "type": "Property",
                                    "observedAt": "2020-12-10T16:30:12.000Z",
                                    "value": {
                                        "@type": "commandResult",
                                        "@value": {
                                            "status": 32,
                                            "random": "value",
                                        },
                                    },
                                },
                            },
                            {
                                "id": "urn:ngsi-ld:Device:filling002",
                                "type": "TestDevice",
                                "m1": {
                                    "type": "Property",
                                    "value": 0.50,
                                    "observedAt": "2020-12-09T16:25:12.000Z",
                                },
                            },
                        ],
                    },
                ),
                DataNotification(
                    notified_at=timestamp_from("2024-01-01T00:00:00"),
                    data=[
                        EntityDataNotification(
                            urn="urn:ngsi-ld:Device:filling001",
                            tenant="test",
                            scope="/",
                            type="FillingLevelSensor",
                            db_id=None,
                            notified_at=timestamp_from("2024-01-01T00:00:00"),
                            data=[
                                EntityAttr(
                                    name="filling-old",
                                    value=0.50,
                                    type=EntityAttrType.PROPERTY,
                                    timestamp=timestamp_from("2020-12-08T16:26:12"),
                                    units="C63",
                                ),
                                EntityAttr(
                                    name="filling",
                                    value=0.25,
                                    type=EntityAttrType.PROPERTY,
                                    timestamp=timestamp_from("2020-12-09T16:27:12"),
                                    units="C62",
                                ),
                                EntityAttr(
                                    name="temperature",
                                    value=32,
                                    type=EntityAttrType.PROPERTY,
                                    timestamp=timestamp_from("2020-12-09T16:28:12"),
                                    units="C",
                                ),
                                EntityAttr(
                                    name="controlledAsset",
                                    value="urn:ngsi-ld:Building:farm001",
                                    type=EntityAttrType.RELATIONSHIP,
                                    timestamp=timestamp_from("2020-12-09T16:29:12"),
                                ),
                                EntityAttr(
                                    name="cmd",
                                    value={
                                        "status": 32,
                                        "status_timestamp": timestamp_from(
                                            "2020-12-09T16:30:12"
                                        ),
                                        "info": {
                                            "status": 32,
                                            "random": "value",
                                        },
                                        "info_timestamp": timestamp_from(
                                            "2020-12-10T16:30:12"
                                        ),
                                    },
                                    type=EntityAttrType.COMMAND,
                                    timestamp=timestamp_from("2020-12-10T16:30:12"),
                                    units=None,
                                ),
                            ],
                        ),
                        EntityDataNotification(
                            urn="urn:ngsi-ld:Device:filling002",
                            tenant="test",
                            scope="/",
                            notified_at=timestamp_from("2024-01-01T00:00:00"),
                            type="TestDevice",
                            db_id=None,
                            data=[
                                EntityAttr(
                                    name="m1",
                                    value=0.50,
                                    type=EntityAttrType.PROPERTY,
                                    timestamp=timestamp_from("2020-12-09T16:25:12"),
                                )
                            ],
                        ),
                    ],
                ),
            ),
            # Notification with deleted entity (deletedAt system attribute)
            (
                ContextBrokerNotification(
                    headers={
                        "ngsild-tenant": "libelium",
                        "ngsild-attribute-format": "Normalized",
                    },
                    body={
                        "id": "urn:ngsi-ld:Notification:ce086a80-dcb5-11f0-8200-0a58a9feac02",
                        "type": "Notification",
                        "subscriptionId": "urn:ngsi-ld:subscription:pid:main",
                        "notifiedAt": "2025-12-19T08:36:25.218Z",
                        "data": [
                            {
                                "id": "urn:ngsi-ld:Device:Device_4195",
                                "type": "https://uri.fiware.org/ns/dataModels#Device",
                                "deletedAt": "2025-12-19T08:36:25.218Z",
                            }
                        ],
                    },
                ),
                DataNotification(
                    notified_at=timestamp_from("2025-12-19T08:36:25.218Z"),
                    data=[
                        EntityDataNotification(
                            urn="urn:ngsi-ld:Device:Device_4195",
                            tenant="libelium",
                            scope="/",
                            notified_at=timestamp_from("2025-12-19T08:36:25.218Z"),
                            type="https://uri.fiware.org/ns/dataModels#Device",
                            db_id=None,
                            data=[],
                        ),
                    ],
                ),
            ),
        ],
    )
    def test_translate(
        self,
        notification: ContextBrokerNotification,
        expected_result: EntityDataNotification | None,
    ):
        result = NgsiLdNormalizedNotificationTranslator().translate(notification)
        assert result == expected_result
