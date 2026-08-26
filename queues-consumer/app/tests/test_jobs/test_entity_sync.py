import json
import pytest
import random
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from schemas.entity_data_notification import (
    EntityAttr,
    EntityDataNotification,
)
from models.entity_model import Entity
from schemas.context_broker_notification_schema import ContextBrokerNotification

from datetime import datetime, timedelta
from jobs.sync.entity_sync import EntitySync
from models.crud.crud_entity import get_or_create_entity


@pytest.fixture(scope="class")
def notification():
    return (
        ContextBrokerNotification(
            headers={
                "ngsild-tenant": "pid",
                "fiware-servicepath": "/",
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
    )


@pytest.fixture
def fake_entity() -> Entity:
    return Entity(
        id=1,
        urn="urn:ngsi-ld:Device:filling001",
        datamodel="Device",
        tenant="pid",
        scope="/",
    )


@pytest.fixture
def fake_entity2() -> Entity:
    return Entity(
        id=1,
        urn="urn:ngsi-ld:Device:filling002",
        datamodel="Device",
        tenant="pid",
        scope="/",
    )


@pytest.fixture
def mock_session(mocker):
    # Create a mock for the Session class
    mock_sess = mocker.MagicMock()
    # Set up any required behaviors or return values for the mock session
    return mock_sess


@pytest.fixture
def custom_cfe_block_notification():
    """Notification using a real CFE r_cfe_block structure for testing."""
    # Real data for the r_cfe_block attribute's value (a list of dictionaries)
    cfe_block_value = [
        {
            "r_cfe_timeinstant": 1755784256,
            "r_cfe_detectType": 2,
            "r_cfe_random": 2,
            "r_cfe_visitorId": "37011bf3bdc03bec0c3f2e5e85b48f77c60efb14",
            "r_cfe_rssi": -98,
        },
        {
            "r_cfe_timeinstant": 1755784260,
            "r_cfe_detectType": 1,
            "r_cfe_random": 1,
            "r_cfe_visitorId": "55d965b5823616d62fb169227ff157a0c24e4b51",
            "r_cfe_rssi": -87,
            "r_cfe_ssid": "DIGIFIBRA-PLUS-cS3T",
            "r_cfe_signature": "76b14837280d5c10b8ce44878ebbf9e289748850",
        },
        # Adding a small sample of the other entries to keep the fixture concise
        {
            "r_cfe_timeinstant": 1755784073,
            "r_cfe_detectType": 2,
            "r_cfe_random": 2,
            "r_cfe_visitorId": "378831fa8882dad7b8e797a5fa601810a349a5bc",
            "r_cfe_rssi": -70,
        },
    ]

    # The timestamp from your real data is "2025-08-21 13:51:07"
    # Convert to a Unix timestamp (float) for EntityAttr.timestamp
    # Assuming the provided timestamp is UTC/local time without timezone info and treating it as UTC for simplicity.
    timestamp_str = "2025-08-21 13:51:07"
    notification_timestamp = (
        datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=timezone.utc)
        .timestamp()
    )

    return EntityDataNotification(
        urn="urn:ngsi-ld:CrowdFlowEvent:SPTA808421CE3AC8859C1477653_CFE",
        type="CrowdFlowEvent",
        tenant="libelium",
        scope="/",
        data=[
            # The 'r_cfe_block' attribute containing the list of CFE events
            EntityAttr(
                name="r_cfe_block",
                value=cfe_block_value,
                type="Property",
                timestamp=notification_timestamp,
            ),
            # You can also include a single, key visitorId attribute if needed for other checks
            EntityAttr(
                name="visitorId",
                value="37011bf3bdc03bec0c3f2e5e85b48f77c60efb14",  # Using the visitorId from the latest event in the block
                type="Property",
                # Using the latest r_cfe_timeinstant (1755784260) for the most recent timestamp
                timestamp=1755784260,
            ),
        ],
    )


@pytest.fixture
def cfe_write_notification():
    """Notification for a CFE with a write attribute."""
    now = datetime.now()
    return EntityDataNotification(
        urn="urn:ngsi-ld:CrowdFlowEvent:TestCFE001",
        type="CrowdFlowEvent",
        tenant="pid",
        scope="/",
        data=[
            EntityAttr(
                name="w_some_command",
                value="on",
                type="Property",
                timestamp=now.timestamp(),
            ),
            EntityAttr(
                name="visitorId",
                value="1",
                type="Property",
                timestamp=(now - timedelta(seconds=1)).timestamp(),
            ),
        ],
    )


@pytest.fixture
def new_cfe_notification():
    """Notification for a new-style CFE (without r_cfe_block)."""
    return EntityDataNotification(
        urn="urn:ngsi-ld:CrowdFlowEvent:TestCFE002",
        type="CrowdFlowEvent",
        tenant="pid",
        scope="/",
        data=[
            EntityAttr(
                name="visitorId",
                value="1",
                type="Property",
                timestamp=datetime.now().timestamp(),
            )
        ],
    )


@pytest.fixture
def old_cfe_notification():
    """Notification for an old-style CFE (with r_cfe_block)."""
    return EntityDataNotification(
        urn="urn:ngsi-ld:CrowdFlowEvent:TestCFE003",
        type="CrowdFlowEvent",
        tenant="pid",
        scope="/",
        data=[
            EntityAttr(
                name="r_cfe_block",
                value="...",
                type="Property",
                timestamp=datetime.now().timestamp(),
            ),
            EntityAttr(
                name="visitorId",
                value="1",
                type="Property",
                timestamp=datetime.now().timestamp(),
            ),
        ],
    )


class TestEntitySync:
    def test_init(self, notification):
        assert EntitySync(notification, None)

    def test_checks(self, fake_entity: Entity, fake_entity2: Entity, mock_session):
        mock_session.patch.jobs.sync.entity_sync.get_entity_type_id.return_value = 1
        mock_session.query.return_value.filter.return_value.first.return_value = (
            fake_entity
        )
        assert (
            get_or_create_entity(
                payload={
                    "urn": "urn:ngsi-ld:Device:filling001",
                    "datamodel": "Device",
                    "tenant": "pid",
                    "scope": "/",
                },
                db=mock_session,
            )
            == fake_entity
        )

        mock_session.query.return_value.filter.return_value.first.return_value = (
            fake_entity2
        )

        assert (
            get_or_create_entity(
                payload={
                    "urn": "urn:ngsi-ld:Device:filling002",
                    "datamodel": "Device",
                    "tenant": "pid",
                    "scope": "/",
                },
                db=mock_session,
            )
            == fake_entity2
        )

    def test_enqueue_save_timeseries(self, notification, mock_session):
        entity_sync = EntitySync(notification, mock_session)

        with pytest.raises(Exception):
            entity_sync.enqueue_save_timeseries(None, None, None)

    @pytest.mark.parametrize(
        "notification_fixture, random_return, should_be_called, description",
        [
            (
                "custom_cfe_block_notification",
                None,
                True,
                "Should always call on write attribute",
            ),
            # This fixture has r_cfe_block -> NEW device -> should always be called
            (
                "old_cfe_notification",
                None,
                True,
                "Should always call for new CFE (with r_cfe_block)",
            ),
            # This fixture has NO r_cfe_block -> OLD device -> should be sampled
            (
                "new_cfe_notification",
                0.005,
                True,
                "Should call for old CFE (no r_cfe_block) when sampled",
            ),
            (
                "new_cfe_notification",
                0.5,
                False,
                "Should NOT call for old CFE (no r_cfe_block) when not sampled",
            ),
        ],
    )
    def test_save_cfe_commands_logic(
        self,
        notification_fixture,
        random_return,
        should_be_called,
        description,
        request,
        mock_session,
        mocker,
    ):
        """
        Tests the logic of save_cfe_commands for different CFE scenarios.
        This test assumes the corrected logic where `is_old_smsp` is True
        when 'r_cfe_block' is present.
        """
        notification = request.getfixturevalue(notification_fixture)

        entity_sync = EntitySync(
            payload=MagicMock(), db=mock_session, realtime_db=mock_session
        )

        mock_enqueue = mocker.patch.object(entity_sync, "enqueue_save_realtime")

        if random_return is not None:
            mocker.patch(
                "jobs.sync.entity_sync.random.random", return_value=random_return
            )

        entity_sync.save_cfe_commands(notification)

        if should_be_called:
            mock_enqueue.assert_called_once_with(notification)
        else:
            mock_enqueue.assert_not_called()


class TestIsDeletionNotification:
    """_is_deletion_notification detects root-level deletedAt on any payload entity."""

    def _entity_sync(self, body):
        return EntitySync(ContextBrokerNotification(headers={"ngsild-tenant": "t"}, body=body))

    def test_returns_true_when_deletedAt_present(self):
        body = {
            "data": [
                {
                    "id": "urn:ngsi-ld:Device:Device_4195",
                    "type": "Device",
                    "deletedAt": "2025-12-19T08:36:25.218Z",
                }
            ],
        }
        assert self._entity_sync(body)._is_deletion_notification() is True

    def test_returns_false_for_regular_notification(self):
        body = {
            "data": [
                {
                    "id": "urn:ngsi-ld:Device:Device_4195",
                    "type": "Device",
                    "temperature": {"type": "Property", "value": 21.5},
                }
            ],
        }
        assert self._entity_sync(body)._is_deletion_notification() is False

    def test_returns_false_when_data_missing(self):
        assert self._entity_sync({})._is_deletion_notification() is False

    def test_returns_true_when_any_entity_is_deleted(self):
        body = {
            "data": [
                {"id": "a", "type": "Device", "temperature": {"type": "Property", "value": 1}},
                {"id": "b", "type": "Device", "deletedAt": "2025-12-19T08:36:25.218Z"},
            ],
        }
        assert self._entity_sync(body)._is_deletion_notification() is True
