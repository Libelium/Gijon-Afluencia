from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from jobs.sync.notification_processor.location_synchronizer import LocationSynchronizer
from models.entity_properties_model import EntityProperty


@pytest.fixture
def mock_realtime_db():
    db = MagicMock()
    return db


@pytest.fixture
def location_synchronizer(mock_realtime_db):
    return LocationSynchronizer(main_db=MagicMock(), realtime_db=mock_realtime_db)


class TestSyncEntityLocations:

    def test_updates_entities_with_different_location(
        self, location_synchronizer, mock_realtime_db
    ):
        """Entities with a different location value should be updated."""
        locations = {
            "1": {
                "urn": "urn:ngsi-ld:TestDevice:Device001",
                "tenant": "pid",
                "scope": "/",
                "location": {
                    "id": 1,
                    "value": {"type": "Point", "coordinates": [1, 2]},
                    "value_type": "string",
                    "timestamp": datetime.fromisoformat("2025-01-01T00:00:00"),
                },
            },
        }
        latest_location = {
            "value": {"type": "Point", "coordinates": [5, 6]},
            "value_type": "string",
            "timestamp": datetime.fromisoformat("2025-01-03T00:00:00"),
        }

        with patch(
            "jobs.sync.notification_processor.location_synchronizer.save_timeseries_job"
        ):
            location_synchronizer._LocationSynchronizer__sync_entity_locations(
                locations, latest_location
            )

        mock_realtime_db.bulk_update_mappings.assert_called_once()
        args = mock_realtime_db.bulk_update_mappings.call_args
        assert args[0][0] == EntityProperty
        assert len(args[0][1]) == 1
        assert args[0][1][0]["id"] == 1
        mock_realtime_db.commit.assert_called_once()

    def test_inserts_location_for_entities_without_one(
        self, location_synchronizer, mock_realtime_db
    ):
        """Entities without a location should get a new one inserted."""
        locations = {
            "1": {
                "urn": "urn:ngsi-ld:TestDevice:Device001",
                "tenant": "pid",
                "scope": "/",
            },
        }
        latest_location = {
            "value": {"type": "Point", "coordinates": [5, 6]},
            "value_type": "string",
            "timestamp": datetime.fromisoformat("2025-01-03T00:00:00"),
        }

        with patch(
            "jobs.sync.notification_processor.location_synchronizer.save_timeseries_job"
        ):
            location_synchronizer._LocationSynchronizer__sync_entity_locations(
                locations, latest_location
            )

        mock_realtime_db.add_all.assert_called_once()
        inserted = mock_realtime_db.add_all.call_args[0][0]
        assert len(inserted) == 1
        assert isinstance(inserted[0], EntityProperty)
        assert inserted[0].entity_id == "1"
        assert inserted[0].name == "location"
        mock_realtime_db.commit.assert_called_once()

    def test_skips_entities_with_same_location(
        self, location_synchronizer, mock_realtime_db
    ):
        """Entities whose location already matches should be skipped entirely."""
        locations = {
            "1": {
                "urn": "urn:ngsi-ld:TestDevice:Device001",
                "tenant": "pid",
                "scope": "/",
                "location": {
                    "id": 1,
                    "value": {"type": "Point", "coordinates": [5, 6]},
                    "value_type": "string",
                    "timestamp": datetime.fromisoformat("2025-01-01T00:00:00"),
                },
            },
        }
        latest_location = {
            "value": {"type": "Point", "coordinates": [5, 6]},
            "value_type": "string",
            "timestamp": datetime.fromisoformat("2025-01-03T00:00:00"),
        }

        with patch(
            "jobs.sync.notification_processor.location_synchronizer.save_timeseries_job"
        ) as mock_ts_job:
            location_synchronizer._LocationSynchronizer__sync_entity_locations(
                locations, latest_location
            )

        mock_realtime_db.add_all.assert_not_called()
        mock_realtime_db.bulk_update_mappings.assert_not_called()
        mock_realtime_db.commit.assert_not_called()
        mock_ts_job.assert_not_called()

    def test_no_commit_when_no_changes(
        self, location_synchronizer, mock_realtime_db
    ):
        """When all entities already have the latest location, no DB operations should happen."""
        locations = {
            "1": {
                "urn": "urn:ngsi-ld:TestDevice:Device001",
                "tenant": "pid",
                "scope": "/",
                "location": {
                    "id": 1,
                    "value": {"type": "Point", "coordinates": [5, 6]},
                    "value_type": "string",
                    "timestamp": datetime.fromisoformat("2025-01-03T00:00:00"),
                },
            },
            "2": {
                "urn": "urn:ngsi-ld:TestDevice:Device002",
                "tenant": "pid",
                "scope": "/",
                "location": {
                    "id": 2,
                    "value": {"type": "Point", "coordinates": [5, 6]},
                    "value_type": "string",
                    "timestamp": datetime.fromisoformat("2025-01-02T00:00:00"),
                },
            },
        }
        latest_location = {
            "value": {"type": "Point", "coordinates": [5, 6]},
            "value_type": "string",
            "timestamp": datetime.fromisoformat("2025-01-03T00:00:00"),
        }

        with patch(
            "jobs.sync.notification_processor.location_synchronizer.save_timeseries_job"
        ):
            location_synchronizer._LocationSynchronizer__sync_entity_locations(
                locations, latest_location
            )

        mock_realtime_db.commit.assert_not_called()

    def test_mixed_insert_update_and_timeseries_sync(
        self, location_synchronizer, mock_realtime_db
    ):
        """When some entities need updates and others need inserts, both realtime and timescale should be synced."""
        locations = {
            "1": {
                "urn": "urn:ngsi-ld:TestDevice:Device001",
                "tenant": "pid",
                "scope": "/",
                "location": {
                    "id": 1,
                    "value": {"type": "Point", "coordinates": [1, 2]},
                    "value_type": "string",
                    "timestamp": datetime.fromisoformat("2025-01-01T00:00:00"),
                },
            },
            "2": {
                "urn": "urn:ngsi-ld:TestDevice:Device002",
                "tenant": "pid",
                "scope": "/",
            },
            "3": {
                "urn": "urn:ngsi-ld:TestDevice:Device003",
                "tenant": "pid",
                "scope": "/",
                "location": {
                    "id": 3,
                    "value": {"type": "Point", "coordinates": [5, 6]},
                    "value_type": "string",
                    "timestamp": datetime.fromisoformat("2025-01-02T00:00:00"),
                },
            },
        }
        latest_location = {
            "value": {"type": "Point", "coordinates": [5, 6]},
            "value_type": "string",
            "timestamp": datetime.fromisoformat("2025-01-03T00:00:00"),
        }

        with patch(
            "jobs.sync.notification_processor.location_synchronizer.save_timeseries_job"
        ) as mock_ts_job:
            location_synchronizer._LocationSynchronizer__sync_entity_locations(
                locations, latest_location
            )

        # --- Realtime DB assertions ---

        # Entity 1 has different location -> update
        mock_realtime_db.bulk_update_mappings.assert_called_once()
        updates = mock_realtime_db.bulk_update_mappings.call_args[0][1]
        assert len(updates) == 1
        assert updates[0]["id"] == 1

        # Entity 2 has no location -> insert
        mock_realtime_db.add_all.assert_called_once()
        inserts = mock_realtime_db.add_all.call_args[0][0]
        assert len(inserts) == 1
        assert inserts[0].entity_id == "2"

        # Entity 3 has same location -> skipped
        mock_realtime_db.commit.assert_called_once()

        # --- TimescaleDB assertions ---

        # Entity 1 (updated) and entity 2 (inserted) should trigger timeseries sync
        # Entity 3 (same location) should be skipped
        assert mock_ts_job.call_count == 2

        notifications = [c[0][0] for c in mock_ts_job.call_args_list]

        # Entity 1: updated location
        assert notifications[0].urn == "urn:ngsi-ld:TestDevice:Device001"
        assert notifications[0].db_id == 1
        assert notifications[0].type == "TestDevice"
        assert notifications[0].data[0].name == "location"
        assert notifications[0].data[0].value == {"type": "Point", "coordinates": [5, 6]}
        assert notifications[0].data[0].timestamp == datetime.fromisoformat("2025-01-03T00:00:00").timestamp()

        # Entity 2: new location (insert)
        assert notifications[1].urn == "urn:ngsi-ld:TestDevice:Device002"
        assert notifications[1].db_id == 2
        assert notifications[1].data[0].value == {"type": "Point", "coordinates": [5, 6]}

    def test_timeseries_error_does_not_prevent_db_operations(
        self, location_synchronizer, mock_realtime_db
    ):
        """If timeseries sync fails, the DB insert/update should still proceed."""
        locations = {
            "1": {
                "urn": "urn:ngsi-ld:TestDevice:Device001",
                "tenant": "pid",
                "scope": "/",
                "location": {
                    "id": 1,
                    "value": {"type": "Point", "coordinates": [1, 2]},
                    "value_type": "string",
                    "timestamp": datetime.fromisoformat("2025-01-01T00:00:00"),
                },
            },
        }
        latest_location = {
            "value": {"type": "Point", "coordinates": [5, 6]},
            "value_type": "string",
            "timestamp": datetime.fromisoformat("2025-01-03T00:00:00"),
        }

        with patch(
            "jobs.sync.notification_processor.location_synchronizer.save_timeseries_job",
            side_effect=Exception("TimescaleDB error"),
        ):
            location_synchronizer._LocationSynchronizer__sync_entity_locations(
                locations, latest_location
            )

        mock_realtime_db.bulk_update_mappings.assert_called_once()
        mock_realtime_db.commit.assert_called_once()
