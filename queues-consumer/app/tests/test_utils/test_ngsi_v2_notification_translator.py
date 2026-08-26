from datetime import datetime
import dateutil.parser
from schemas.context_broker_notification_schema import ContextBrokerNotification
from schemas.entity_data_notification import (
    CommandAttrValue,
    DataNotification,
    EntityAttr,
    EntityDataNotification,
)
from utils.ngsi.cb_notification_translator.ngsi_v2_notification_translator import (
    NgsiV2NormalizedNotificationTranslator,
)
import pytest
import freezegun


@pytest.fixture(scope="class")
def translator() -> NgsiV2NormalizedNotificationTranslator:
    return NgsiV2NormalizedNotificationTranslator()


def timestamp_from(date_str: str):
    # witout timezone
    date = dateutil.parser.parse(date_str)
    return date.timestamp()


def date_from(date_str: str):
    # witout timezone
    date = dateutil.parser.parse(date_str)
    return date


# it should be a leap year to avoid problems
def reference_time() -> str:
    return "2024-05-23T11:55:11.750Z"


class TestNgsiV2NotificationTranslator:

    @pytest.mark.parametrize(
        ("attr_name", "attr_value", "default_timestamp", "expected_result"),
        [
            (
                "temperature",
                {
                    "type": "Number",
                    "value": 25.0,
                    "metadata": {
                        "TimeInstant": {
                            "type": "DateTime",
                            "value": "2021-08-13T00:00:00.000Z",
                        },
                        "UnitCode": {"value": "Celsius"},
                    },
                },
                date_from("2021-08-25T00:00:00.000Z"),
                EntityAttr(
                    name="temperature",
                    value=25.0,
                    type="Property",
                    units="Celsius",
                    timestamp=timestamp_from("2021-08-13T00:00:00.000Z"),
                ),
            ),
            (
                "temperature",
                {
                    "type": "Number",
                    "value": 25.0,
                    "metadata": {
                        "TimeInstant": {
                            "type": "DateTime",
                            "value": "2021-08-13T00:00:00.000Z",
                        },
                    },
                },
                date_from("2021-08-25T00:00:00.000Z"),
                EntityAttr(
                    name="temperature",
                    value=25.0,
                    type="Property",
                    units=None,
                    timestamp=timestamp_from("2021-08-13T00:00:00.000Z"),
                ),
            ),
            (
                "temperature",
                {
                    "type": "Number",
                    "value": 25.0,
                },
                date_from("2021-08-25T00:00:00.000Z"),
                EntityAttr(
                    name="temperature",
                    value=25.0,
                    type="Property",
                    units=None,
                    timestamp_override=True,
                    timestamp=timestamp_from("2021-08-25T00:00:00.000Z"),
                ),
            ),
            (
                "neighbor",
                {
                    "type": "Relationship",
                    "value": "urn:ngsi-ld:Room:001",
                },
                date_from("2021-08-25T00:00:00.000Z"),
                EntityAttr(
                    name="neighbor",
                    value="urn:ngsi-ld:Room:001",
                    type="Relationship",
                    units=None,
                    timestamp_override=True,
                    timestamp=timestamp_from("2021-08-25T00:00:00.000Z"),
                ),
            ),
            (
                "cmd",
                {
                    "type": "command",
                    "value": "open",
                },
                date_from("2021-08-25T00:00:00.000Z"),
                EntityAttr(
                    name="cmd",
                    value="open",
                    type="Property",
                    units=None,
                    timestamp_override=True,
                    timestamp=timestamp_from("2021-08-25T00:00:00.000Z"),
                ),
            ),
            (
                "cmd_info",
                {
                    "type": "commandResult",
                    "value": "success",
                    "metadata": {
                        "TimeInstant": {
                            "type": "DateTime",
                            "value": "2021-08-13T00:00:00.000Z",
                        },
                    },
                },
                date_from("2021-08-25T00:00:00.000Z"),
                EntityAttr(
                    name="cmd",
                    value=CommandAttrValue(
                        info="success",
                        status=None,
                        info_timestamp=timestamp_from("2021-08-13T00:00:00.000Z"),
                        status_timestamp=0,
                    ),
                    type="Command",
                    units=None,
                    timestamp=timestamp_from("2021-08-13T00:00:00.000Z"),
                ),
            ),
            (
                "cmd_status",
                {
                    "type": "commandStatus",
                    "value": "success",
                    "metadata": {
                        "TimeInstant": {
                            "type": "DateTime",
                            "value": "2021-08-13T00:00:00.000Z",
                        },
                    },
                },
                date_from("2021-08-25T00:00:00.000Z"),
                EntityAttr(
                    name="cmd",
                    value=CommandAttrValue(
                        info=None,
                        status="success",
                        info_timestamp=0,
                        status_timestamp=timestamp_from("2021-08-13T00:00:00.000Z"),
                    ),
                    type="Command",
                    units=None,
                    timestamp=timestamp_from("2021-08-13T00:00:00.000Z"),
                ),
            ),
        ],
    )
    def test_translate_normalized_attribute(
        self,
        attr_name: str,
        attr_value: dict,
        default_timestamp: datetime,
        expected_result: EntityAttr,
        translator: NgsiV2NormalizedNotificationTranslator,
    ):
        assert (
            translator._NgsiV2NormalizedNotificationTranslator__translate_normalized_attribute(
                attr_name, attr_value, default_timestamp
            )
            == expected_result
        )

    @pytest.mark.parametrize(
        ("cmd_info", "cmd_status", "expected_result"),
        [
            (
                EntityAttr(
                    name="cmd",
                    value=CommandAttrValue(
                        info="success",
                        status=None,
                        info_timestamp=timestamp_from("2021-08-14T00:00:00.000Z"),
                        status_timestamp=0,
                    ),
                    type="Command",
                    units=None,
                    timestamp=timestamp_from("2021-08-14T00:00:00.000Z"),
                ),
                EntityAttr(
                    name="cmd",
                    value=CommandAttrValue(
                        info=None,
                        status="status",
                        info_timestamp=0,
                        status_timestamp=timestamp_from("2021-08-13T00:00:00.000Z"),
                    ),
                    type="Command",
                    units=None,
                    timestamp=timestamp_from("2021-08-13T00:00:00.000Z"),
                ),
                EntityAttr(
                    name="cmd",
                    value=CommandAttrValue(
                        info="success",
                        status="status",
                        info_timestamp=timestamp_from("2021-08-14T00:00:00.000Z"),
                        status_timestamp=timestamp_from("2021-08-13T00:00:00.000Z"),
                    ),
                    type="Command",
                    units=None,
                    timestamp=timestamp_from("2021-08-14T00:00:00.000Z"),
                ),
            ),
            (
                EntityAttr(
                    name="cmd",
                    value=CommandAttrValue(
                        info="success",
                        status=None,
                        info_timestamp=timestamp_from("2021-08-14T00:00:00.000Z"),
                        status_timestamp=0,
                    ),
                    type="Command",
                    units=None,
                    timestamp=timestamp_from("2021-08-14T00:00:00.000Z"),
                ),
                EntityAttr(
                    name="cmd2",
                    value=CommandAttrValue(
                        info=None,
                        status="status",
                        info_timestamp=0,
                        status_timestamp=timestamp_from("2021-08-13T00:00:00.000Z"),
                    ),
                    type="Command",
                    units=None,
                    timestamp=timestamp_from("2021-08-13T00:00:00.000Z"),
                ),
                None,
            ),
        ],
    )
    def test_merge_info_status(
        self,
        cmd_info: EntityAttr,
        cmd_status: EntityAttr,
        expected_result: EntityAttr,
        translator: NgsiV2NormalizedNotificationTranslator,
    ):
        try:
            assert (
                translator._NgsiV2NormalizedNotificationTranslator__merge_cmd_info_status(
                    cmd_info, cmd_status
                )
                == expected_result
            )
        except ValueError:
            assert cmd_info.name != cmd_status.name

    @pytest.mark.parametrize(
        ("entity", "default_timestamp", "tenant", "scope", "expected_result"),
        [
            (
                {
                    "id": "urn:ngsi-ld:Room:001",
                    "type": "Room",
                    "temperature": {
                        "type": "Number",
                        "value": 25.0,
                        "metadata": {
                            "TimeInstant": {
                                "type": "DateTime",
                                "value": "2021-08-13T00:00:00.000Z",
                            },
                            "UnitCode": {"value": "Celsius"},
                        },
                    },
                    "neighbor": {
                        "type": "Relationship",
                        "value": "urn:ngsi-ld:Room:002",
                    },
                },
                date_from("2021-08-25T00:00:00.000Z"),
                "tenant",
                "scope",
                EntityDataNotification(
                    urn="urn:ngsi-ld:Room:001",
                    notified_at=timestamp_from("2021-08-25T00:00:00.000Z"),
                    tenant="tenant",
                    scope="scope",
                    type="Room",
                    db_id=None,
                    data=[
                        EntityAttr(
                            name="temperature",
                            value=25.0,
                            type="Property",
                            units="Celsius",
                            timestamp=timestamp_from("2021-08-13T00:00:00.000Z"),
                        ),
                        EntityAttr(
                            name="neighbor",
                            value="urn:ngsi-ld:Room:002",
                            type="Relationship",
                            timestamp_override=True,
                            units=None,
                            timestamp=timestamp_from("2021-08-25T00:00:00.000Z"),
                        ),
                    ],
                ),
            ),
            (
                {
                    "id": "urn:ngsi-ld:Room:001",
                    "type": "Room",
                    "cmd": {
                        "type": "command",
                        "value": "open",
                        "metadata": {
                            "TimeInstant": {
                                "type": "DateTime",
                                "value": "2021-08-12T00:00:00.000Z",
                            }
                        },
                    },
                    "cmd_info": {
                        "type": "commandResult",
                        "value": "success",
                        "metadata": {
                            "TimeInstant": {
                                "type": "DateTime",
                                "value": "2021-08-13T00:00:00.000Z",
                            }
                        },
                    },
                    "cmd_status": {
                        "type": "commandStatus",
                        "value": "status",
                        "metadata": {
                            "TimeInstant": {
                                "type": "DateTime",
                                "value": "2021-08-14T00:00:00.000Z",
                            }
                        },
                    },
                },
                date_from("2021-08-25T00:00:00.000Z"),
                "tenant",
                "scope",
                EntityDataNotification(
                    urn="urn:ngsi-ld:Room:001",
                    tenant="tenant",
                    notified_at=timestamp_from("2021-08-25T00:00:00.000Z"),
                    scope="scope",
                    type="Room",
                    db_id=None,
                    data=[
                        EntityAttr(
                            name="cmd",
                            value="open",
                            type="Property",
                            units=None,
                            timestamp=timestamp_from("2021-08-12T00:00:00.000Z"),
                        ),
                        EntityAttr(
                            name="cmd",
                            value=CommandAttrValue(
                                info="success",
                                status="status",
                                info_timestamp=timestamp_from(
                                    "2021-08-13T00:00:00.000Z"
                                ),
                                status_timestamp=timestamp_from(
                                    "2021-08-14T00:00:00.000Z"
                                ),
                            ).dict(),
                            type="Command",
                            units=None,
                            timestamp=timestamp_from("2021-08-14T00:00:00.000Z"),
                        ),
                    ],
                ),
            ),
        ],
    )
    def test_entity_translation(
        self,
        entity: dict,
        default_timestamp: datetime,
        tenant: str,
        scope: str,
        expected_result: EntityDataNotification,
        translator: NgsiV2NormalizedNotificationTranslator,
    ):
        assert (
            translator.translate_entity(entity, default_timestamp, tenant, scope)
            == expected_result
        )

    @pytest.mark.parametrize(
        ("notification", "expected_result"),
        [
            (
                ContextBrokerNotification(
                    headers={"fiware-service": "tenant", "fiware-servicepath": "scope"},
                    body={
                        "subscriptionId": "664f2d9b43b89e36c20c7cee",
                        "data": [
                            {
                                "id": "urn:ngsi-ld:Motion:001",
                                "type": "Device",
                                "TimeInstant": {
                                    "type": "DateTime",
                                    "value": "2024-05-23T11:51:11.750Z",
                                    "metadata": {},
                                },
                                "count": {
                                    "type": "Integer",
                                    "value": 1,
                                    "metadata": {
                                        "TimeInstant": {
                                            "type": "DateTime",
                                            "value": "2024-05-23T11:51:11.662Z",
                                        }
                                    },
                                },
                                "dis": {
                                    "type": "Text",
                                    "value": "V",
                                    "metadata": {
                                        "TimeInstant": {
                                            "type": "DateTime",
                                            "value": "2024-05-23T11:51:11.662Z",
                                        }
                                    },
                                },
                                "refStore": {
                                    "type": "Relationship",
                                    "value": "urn:ngsi-ld:Store:001",
                                    "metadata": {
                                        "TimeInstant": {
                                            "type": "DateTime",
                                            "value": "2024-05-23T11:51:11.750Z",
                                        }
                                    },
                                },
                                "ring_info": {
                                    "type": "commandResult",
                                    "value": " ",
                                    "metadata": {
                                        "TimeInstant": {
                                            "type": "DateTime",
                                            "value": "2024-05-23T11:51:11.750Z",
                                        }
                                    },
                                },
                                "ring_status": {
                                    "type": "commandStatus",
                                    "value": "DELIVERED",
                                    "metadata": {
                                        "TimeInstant": {
                                            "type": "DateTime",
                                            "value": "2024-05-23T11:51:11.751Z",
                                        }
                                    },
                                },
                            }
                        ],
                    },
                ),
                DataNotification(
                    notified_at=timestamp_from(reference_time()),
                    data=[
                        EntityDataNotification(
                            notified_at=timestamp_from(reference_time()),
                            urn="urn:ngsi-ld:Motion:001",
                            tenant="tenant",
                            scope="scope",
                            type="Device",
                            db_id=None,
                            data=[
                                EntityAttr(
                                    name="count",
                                    value=1,
                                    type="Property",
                                    units=None,
                                    timestamp=timestamp_from(
                                        "2024-05-23T11:51:11.662Z"
                                    ),
                                ),
                                EntityAttr(
                                    name="dis",
                                    value="V",
                                    type="Property",
                                    units=None,
                                    timestamp=timestamp_from(
                                        "2024-05-23T11:51:11.662Z"
                                    ),
                                ),
                                EntityAttr(
                                    name="refStore",
                                    value="urn:ngsi-ld:Store:001",
                                    type="Relationship",
                                    units=None,
                                    timestamp=timestamp_from(
                                        "2024-05-23T11:51:11.750Z"
                                    ),
                                ),
                                EntityAttr(
                                    name="ring",
                                    value=CommandAttrValue(
                                        info=" ",
                                        status="DELIVERED",
                                        info_timestamp=timestamp_from(
                                            "2024-05-23T11:51:11.750Z"
                                        ),
                                        status_timestamp=timestamp_from(
                                            "2024-05-23T11:51:11.751Z"
                                        ),
                                    ).dict(),
                                    type="Command",
                                    units=None,
                                    timestamp=timestamp_from(
                                        "2024-05-23T11:51:11.751Z"
                                    ),
                                ),
                            ],
                        )
                    ],
                ),
            ),
        ],
    )
    @freezegun.freeze_time(reference_time())
    def test_translate_notification(
        self,
        notification: ContextBrokerNotification,
        expected_result: DataNotification,
        translator: NgsiV2NormalizedNotificationTranslator,
    ):
        assert translator.translate(notification) == expected_result
