from datetime import datetime
from typing import Any, Dict
import pytest
from db import deps, realtime
from jobs.sync.notification_processor.location_synchronizer import LocationSynchronizer
from jobs.sync.notification_processor.notification_processor_pipeline import (
    NotificationProcessorPipeline,
)
from schemas.entity_data_notification import EntityAttr, EntityDataNotification


@pytest.fixture
def location_synchronizer():
    return LocationSynchronizer(main_db=None, realtime_db=None)


class TestLocationSynchronizer:

    @pytest.mark.parametrize(
        (
            "locations",
            "notification",
            "expected_latest_location",
            "expedted_notification",
        ),
        [
            # TEST CASE 1
            (
                {
                    "1": {
                        "urn": "urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                        "tenant": "pid",
                        "scope": "/",
                        "location": {
                            "id": 1,
                            "value": {
                                "type": "Point",
                                "coordinates": [1, 2],
                            },
                            "value_type": "string",
                            "timestamp": datetime.fromisoformat("2025-01-01T00:00:00"),
                        },
                    },
                    "2": {
                        "urn": "urn:ngsi-ld:TestDevice:TestLocationSyncDevice002",
                        "tenant": "pid",
                        "scope": "/",
                        "location": {
                            "id": 2,
                            "value": {
                                "type": "Point",
                                "coordinates": [3, 4],
                            },
                            "value_type": "string",
                            "timestamp": datetime.fromisoformat("2025-01-02T00:00:00"),
                        },
                    },
                },
                EntityDataNotification(
                    urn="urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                    tenant="pid",
                    scope="/",
                    type="TestDevice",
                    notified_at=1742888776.151,
                    devices=[934],
                    db_id=0,
                    data=[
                        EntityAttr(
                            name="location",
                            value={
                                "type": "Point",
                                "coordinates": [5, 6],
                            },
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-03T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                        EntityAttr(
                            name="temperature",
                            value=14,
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-01T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                    ],
                ),
                {
                    "value": {
                        "type": "Point",
                        "coordinates": [5, 6],
                    },
                    "value_type": "string",
                    "timestamp": datetime.fromisoformat("2025-01-03T00:00:00"),
                },
                EntityDataNotification(
                    urn="urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                    tenant="pid",
                    scope="/",
                    type="TestDevice",
                    notified_at=1742888776.151,
                    devices=[934],
                    db_id=0,
                    data=[
                        EntityAttr(
                            name="location",
                            value={
                                "type": "Point",
                                "coordinates": [5, 6],
                            },
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-03T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                        EntityAttr(
                            name="temperature",
                            value=14,
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-01T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                    ],
                ),
            ),
            # TEST CASE 2
            (
                {
                    "1": {
                        "urn": "urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                        "tenant": "pid",
                        "scope": "/",
                        "location": {
                            "id": 1,
                            "value": {
                                "type": "Point",
                                "coordinates": [1, 2],
                            },
                            "value_type": "string",
                            "timestamp": datetime.fromisoformat("2025-01-04T00:00:00"),
                        },
                    },
                    "2": {
                        "urn": "urn:ngsi-ld:TestDevice:TestLocationSyncDevice002",
                        "tenant": "pid",
                        "scope": "/",
                        "location": {
                            "id": 2,
                            "value": {
                                "type": "Point",
                                "coordinates": [3, 4],
                            },
                            "value_type": "string",
                            "timestamp": datetime.fromisoformat("2025-01-02T00:00:00"),
                        },
                    },
                },
                EntityDataNotification(
                    urn="urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                    tenant="pid",
                    scope="/",
                    type="TestDevice",
                    notified_at=1742888776.151,
                    devices=[934],
                    db_id=0,
                    data=[
                        EntityAttr(
                            name="location",
                            value={
                                "type": "Point",
                                "coordinates": [5, 6],
                            },
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-03T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                        EntityAttr(
                            name="temperature",
                            value=14,
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-01T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                    ],
                ),
                {
                    "id": 1,
                    "value": {
                        "type": "Point",
                        "coordinates": [1, 2],
                    },
                    "value_type": "string",
                    "timestamp": datetime.fromisoformat("2025-01-04T00:00:00"),
                },
                EntityDataNotification(
                    urn="urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                    tenant="pid",
                    scope="/",
                    type="TestDevice",
                    notified_at=1742888776.151,
                    devices=[934],
                    db_id=0,
                    data=[
                        EntityAttr(
                            name="location",
                            value={
                                "type": "Point",
                                "coordinates": [1, 2],
                            },
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-04T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                        EntityAttr(
                            name="temperature",
                            value=14,
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-01T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                    ],
                ),
            ),
            # TEST CASE 3
            (
                {
                    "1": {
                        "urn": "urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                        "tenant": "pid",
                        "scope": "/",
                    },
                    "2": {
                        "urn": "urn:ngsi-ld:TestDevice:TestLocationSyncDevice002",
                        "tenant": "pid",
                        "scope": "/",
                    },
                },
                EntityDataNotification(
                    urn="urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                    tenant="pid",
                    scope="/",
                    type="TestDevice",
                    notified_at=1742888776.151,
                    devices=[934],
                    db_id=0,
                    data=[
                        EntityAttr(
                            name="temperature",
                            value=14,
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-01T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                    ],
                ),
                None,
                EntityDataNotification(
                    urn="urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                    tenant="pid",
                    scope="/",
                    type="TestDevice",
                    notified_at=1742888776.151,
                    devices=[934],
                    db_id=0,
                    data=[
                        EntityAttr(
                            name="temperature",
                            value=14,
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-01T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                    ],
                ),
            ),
            # TEST CASE 4
            (
                {
                    "1": {
                        "urn": "urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                        "tenant": "pid",
                        "scope": "/",
                        "location": {
                            "id": 1,
                            "value": {
                                "type": "Point",
                                "coordinates": [1, 2],
                            },
                            "value_type": "string",
                            "timestamp": datetime.fromisoformat("2025-01-04T00:00:00"),
                        },
                    },
                    "2": {
                        "urn": "urn:ngsi-ld:TestDevice:TestLocationSyncDevice002",
                        "tenant": "pid",
                        "scope": "/",
                        "location": {
                            "id": 2,
                            "value": {
                                "type": "Point",
                                "coordinates": [3, 4],
                            },
                            "value_type": "string",
                            "timestamp": datetime.fromisoformat("2025-01-02T00:00:00"),
                        },
                    },
                },
                EntityDataNotification(
                    urn="urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                    tenant="pid",
                    scope="/",
                    type="TestDevice",
                    notified_at=1742888776.151,
                    devices=[934],
                    db_id=0,
                    data=[
                        EntityAttr(
                            name="temperature",
                            value=14,
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-01T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                    ],
                ),
                {
                    "id": 1,
                    "value": {
                        "type": "Point",
                        "coordinates": [1, 2],
                    },
                    "value_type": "string",
                    "timestamp": datetime.fromisoformat("2025-01-04T00:00:00"),
                },
                EntityDataNotification(
                    urn="urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                    tenant="pid",
                    scope="/",
                    type="TestDevice",
                    notified_at=1742888776.151,
                    devices=[934],
                    db_id=0,
                    data=[
                        EntityAttr(
                            name="temperature",
                            value=14,
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-01T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                        EntityAttr(
                            name="location",
                            value={
                                "type": "Point",
                                "coordinates": [1, 2],
                            },
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-04T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                    ],
                ),
            ),
            # TEST CASE 5
            (
                {
                    "1": {
                        "urn": "urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                        "tenant": "pid",
                        "scope": "/",
                    },
                    "2": {
                        "urn": "urn:ngsi-ld:TestDevice:TestLocationSyncDevice002",
                        "tenant": "pid",
                        "scope": "/",
                    },
                },
                EntityDataNotification(
                    urn="urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                    tenant="pid",
                    scope="/",
                    type="TestDevice",
                    notified_at=1742888776.151,
                    devices=[934],
                    db_id=0,
                    data=[
                        EntityAttr(
                            name="location",
                            value={
                                "type": "Point",
                                "coordinates": [5, 6],
                            },
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-03T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                        EntityAttr(
                            name="temperature",
                            value=14,
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-01T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                    ],
                ),
                {
                    "value": {
                        "type": "Point",
                        "coordinates": [5, 6],
                    },
                    "value_type": "string",
                    "timestamp": datetime.fromisoformat("2025-01-03T00:00:00"),
                },
                EntityDataNotification(
                    urn="urn:ngsi-ld:TestDevice:TestLocationSyncDevice001",
                    tenant="pid",
                    scope="/",
                    type="TestDevice",
                    notified_at=1742888776.151,
                    devices=[934],
                    db_id=0,
                    data=[
                        EntityAttr(
                            name="location",
                            value={
                                "type": "Point",
                                "coordinates": [5, 6],
                            },
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-03T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                        EntityAttr(
                            name="temperature",
                            value=14,
                            type="Property",
                            units=None,
                            timestamp=datetime.fromisoformat(
                                "2025-01-01T00:00:00"
                            ).timestamp(),
                            timestamp_override=False,
                        ),
                    ],
                ),
            ),
        ],
    )
    def test_notification_update(
        self,
        locations: Dict[str, Dict[str, Any]],
        notification: EntityDataNotification,
        expected_latest_location: Dict,
        expedted_notification: EntityDataNotification,
        location_synchronizer: LocationSynchronizer,
    ):
        result = (
            location_synchronizer._LocationSynchronizer__update_notification_location(
                locations, notification
            )
        )
        assert result == expected_latest_location
        assert notification == expedted_notification
