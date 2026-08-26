import pytest
from mock import MagicMock, patch
from datetime import datetime
from types import SimpleNamespace
from models.entity_model import Entity  # Ajusta al nombre real del archivo


from jobs.sync.mapping_schemas.virtualization.virtualization_ms import VirtualizationMS
from schemas.entity_data_notification import (
    EntityDataNotification,
    EntityAttr,
    EntityAttrType,
)
from models.mapping_schema_model import MappingSchema as MappingSchemaModel


@pytest.fixture
def mock_db_session(mocker):
    mock_session = mocker.MagicMock()
    return mock_session


@pytest.fixture
def destination_entity():
    return Entity(
        id=999,
        urn="urn:ngsi-ld:Device:dest",
        tenant="tenantX",
        scope="scopeX",
        datamodel="Device",
    )


def compare_notif(actual: EntityDataNotification, expected_attrs: list, dest_entity, expected_devices=None):
    """Compara la notificación generada con atributos esperados y metadatos de entidad destino."""

    assert actual.urn == dest_entity.urn
    assert actual.tenant == dest_entity.tenant
    assert actual.scope == dest_entity.scope
    assert actual.type == dest_entity.datamodel
    assert actual.db_id == dest_entity.id

    if expected_devices is not None:
        assert actual.devices == expected_devices

    # Convert to a name->value dict to ignore ordering
    assert {a.name: a.value for a in actual.data} == {
        a.name: a.value for a in expected_attrs
    }


def make_attr(name: str, value: int = 1, ts: float | None = None):
    return EntityAttr(
        name=name,
        value=value,
        type=EntityAttrType.PROPERTY,
        timestamp=ts or datetime.now().timestamp(),
    )


def make_schema(mapping: list | None = None, include: bool | None = None, _id: int = 1):
    if mapping is None:
        mapping = []
    schema_dict = {"mapping": mapping}
    if include is not None:
        schema_dict["include_non_translated"] = include
    return MappingSchemaModel(id=_id, name=f"schema{_id}", map=schema_dict)


def minimal_notification(attrs):
    return EntityDataNotification(
        urn="urn:ngsi-ld:Device:src",
        tenant="t",
        scope="s",
        type="Device",
        db_id=123,
        devices=[],
        data=attrs,
    )


class TestVirtualizationMS:

    @pytest.mark.parametrize(
        (
            "mapping_schema",
            "input_attrs",
            "expected_attrs",
        ),
        [
            # Case 1: simple rename, do not include unmapped attributes
            (
                make_schema(mapping=[{"source_attr": "temp", "target_attr": "temperature"}]),
                [make_attr("temp", value=25), make_attr("hum", value=50)],
                [make_attr("temperature", value=25)],
            ),
            # Case 2: include_non_translated=True
            (
                make_schema(
                    mapping=[{"source_attr": "pressure", "target_attr": "press"}],
                    include=True,
                ),
                [make_attr("pressure", value=1013), make_attr("bat", value=80)],
                [make_attr("press", value=1013), make_attr("bat", value=80)],
            ),
            # Case 3: empty mapping + include=True
            (
                make_schema(mapping=[], include=True),
                [make_attr("co2", value=400)],
                [make_attr("co2", value=400)],
            ),
            # Case 4: mapping None and flag omitted -> discard all attributes
            (
                make_schema(mapping=None, include=None),
                [make_attr("foo", value=1)],
                [],
            ),
            # Case 5: multiple mappings
            (
                make_schema(mapping=[
                    {"source_attr": "temp", "target_attr": "temperature"},
                    {"source_attr": "hum", "target_attr": "humidity"},
                    {"source_attr": "pres", "target_attr": "pressure"},
                ]),
                [make_attr("temp", 20), make_attr("hum", 50), make_attr("pres", 1010)],
                [make_attr("temperature", 20), make_attr("humidity", 50), make_attr("pressure", 1010)],
            ),
            # Case 6: source and target are the same
            (
                make_schema(mapping=[
                    {"source_attr": "status", "target_attr": "status"},
                    {"source_attr": "level", "target_attr": "level"},
                ]),
                [make_attr("status", "ok"), make_attr("level", 5)],
                [make_attr("status", "ok"), make_attr("level", 5)],
            ),
            # Case 7: discard unmapped attribute if include=False
            (
                make_schema(mapping=[{"source_attr": "a", "target_attr": "A"}], include=False),
                [make_attr("a", 1), make_attr("b", 2)],
                [make_attr("A", 1)],  # b is not mapped and should be discarded
            ),
        ],
    )
    def test_apply(
        self,
        mapping_schema,
        input_attrs,
        expected_attrs,
        mock_db_session,
        destination_entity,
    ):
        notification = minimal_notification(input_attrs)

        with patch(
            "models.crud.crud_entity.get_entity_by_id",
            MagicMock(return_value=destination_entity),
        ):
            vms = VirtualizationMS(
                mapping_schema=mapping_schema,
                destination_entity_id=destination_entity.id,
                db=mock_db_session,
            )

            result_list = vms.apply(notification)

        assert len(result_list) == 1
        result_notif = result_list[0]
        compare_notif(result_notif, expected_attrs, destination_entity)

        assert vms.db is mock_db_session

    def test_apply_includes_devices(self, mock_db_session, destination_entity):
        input_attrs = [make_attr("temp", value=22)]
        expected_devices = [101, 102]

        notification = minimal_notification(input_attrs)

        with patch(
            "models.crud.crud_entity.get_entity_by_id",
            MagicMock(return_value=destination_entity),
        ), patch(
            "models.crud.crud_entity.get_related_devices",
            MagicMock(return_value=expected_devices),
        ):
            vms = VirtualizationMS(
                mapping_schema=make_schema(mapping=[], include=True),
                destination_entity_id=destination_entity.id,
                db=mock_db_session,
            )

            result_list = vms.apply(notification)

        assert len(result_list) == 1
        result_notif = result_list[0]
        compare_notif(result_notif, input_attrs, destination_entity, expected_devices=expected_devices)
