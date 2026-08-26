import pytest
from mock import MagicMock, patch

from datetime import datetime

from jobs.sync.mapping_schemas.factory.mapping_schema_factory import MappingSchemaFactory
from jobs.sync.mapping_schemas.virtualization.virtualization_ms import VirtualizationMS

from models.virtualizations_model import Virtualizations
from models.mapping_schema_model import MappingSchema as MappingSchemaModel
from schemas.entity_data_notification import (
    EntityDataNotification,
    EntityAttr,
    EntityAttrType,
)

@pytest.fixture
def mock_db_session(mocker):
    mock_session = mocker.MagicMock()
    return mock_session


@pytest.fixture
def factory():
    return MappingSchemaFactory()


def compare_vms(actual: VirtualizationMS, expected: VirtualizationMS, db):
    assert isinstance(actual, VirtualizationMS)
    assert isinstance(expected, VirtualizationMS)
    assert actual.mapping_schema.id == expected.mapping_schema.id
    assert actual.destination_entity_id == expected.destination_entity_id
    assert actual.db == db

def make_mapping_schema(schema_id: int, name: str = "schema"):
    return MappingSchemaModel(id=schema_id, name=name, map={"mapping": [], "include_non_translated": False})


def make_virtualization(v_id: int, schema_id: int, dest: int, v_type: str):
    return Virtualizations(
        mapping_schema_id=schema_id,
        virtualization_id=v_id,
        virtualization_type=v_type,
        destination_entity_id=dest,
    )


def minimal_notification(db_id: int, devices=None):
    if devices is None:
        devices = []
    attr = EntityAttr(
        name="temp",
        value=25,
        type=EntityAttrType.PROPERTY,
        timestamp=datetime.now().timestamp(),

    )
    return EntityDataNotification(
        urn="urn:ngsi-ld:Device:test",
        tenant="t",
        scope="s",
        type="Device",
        db_id=db_id,
        devices=devices,
        data=[attr],
    )


class TestMappingSchemaFactory:

    @pytest.mark.parametrize(
        (
            "notification",
            "virtualizations_patch_map",
            "mapping_schema_patch_map",
            "expected_instances",
        ),
        [
            # Case 1: notification with one device, one virtualization, no entity virtualization 
            (
                minimal_notification(db_id=5, devices=[101]),
                {
                    ("devices", 101): [make_virtualization(101, 1, 10, "devices")],
                    ("entities", 5): [],
                },
                {1: make_mapping_schema(1)},
                [
                    VirtualizationMS(
                        mapping_schema=make_mapping_schema(1),
                        destination_entity_id=10,
                        db=None,  # will be set in compare
                    )
                ],
            ),
            # Case 2: notification with no devices, entity virtualization present 
            (
                minimal_notification(db_id=7, devices=[]),
                {
                    ("entities", 7): [make_virtualization(7, 2, 20, "entities")],
                },
                {2: make_mapping_schema(2)},
                [
                    VirtualizationMS(
                        mapping_schema=make_mapping_schema(2),
                        destination_entity_id=20,
                        db=None,
                    )
                ],
            ),
            # Case 3: multiple devices each with a virtualization + entity virtualization 
            (
                minimal_notification(db_id=9, devices=[201, 202]),
                {
                    ("devices", 201): [make_virtualization(201, 3, 30, "devices")],
                    ("devices", 202): [make_virtualization(202, 4, 40, "devices")],
                    ("entities", 9): [make_virtualization(9, 5, 50, "entities")],
                },
                {
                    3: make_mapping_schema(3),
                    4: make_mapping_schema(4),
                    5: make_mapping_schema(5),
                },
                [
                    VirtualizationMS(make_mapping_schema(3), 30, None),
                    VirtualizationMS(make_mapping_schema(4), 40, None),
                    VirtualizationMS(make_mapping_schema(5), 50, None),
                ],
            ),
            # Case 4: mapping schema missing (None) -> should be filtered out 
            (
                minimal_notification(db_id=11, devices=[301]),
                {
                    ("devices", 301): [make_virtualization(301, 6, 60, "devices")],
                    ("entities", 11): [],
                },
                {6: None},  # simulate deleted mapping schema
                [],
            ),
        ],
    )
    def test_mapping_schema_factory(
        self,
        notification,
        virtualizations_patch_map,
        mapping_schema_patch_map,
        expected_instances,
        mock_db_session,
        factory,
    ):

        # Side‑effect helpers --------------------------------------------------
        def virtualizations_side_effect(db, v_type, v_id):
            return virtualizations_patch_map.get((v_type, v_id), [])

        def mapping_schema_side_effect(db, schema_id):
            return mapping_schema_patch_map.get(schema_id)

        # Apply patches -------------------------------------------------------
        with patch(
            "models.crud.crud_virtualizations.get_virtualizations_by_type_id",
            MagicMock(side_effect=virtualizations_side_effect),
        ), patch(
            "models.crud.crud_mapping_schema.get_mapping_schema",
            MagicMock(side_effect=mapping_schema_side_effect),
        ):
            result = factory.get_mapping_schemas(mock_db_session, notification)

        assert len(result) == len(expected_instances)

        for actual, expected in zip(result, expected_instances):
            # Clone expected with actual DB for accurate comparison
            expected.db = mock_db_session
            compare_vms(actual, expected, mock_db_session)
