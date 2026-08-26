import datetime
from typing import Any, List
from schemas.entity_data_notification import EntityDataNotification
from jobs.realtime.cmd_status_interpreter.cmd_status_interpreter_factory import (
    CmdStatusInterpreterFactory,
)
from schemas.ngsi_cmd_info_schema import NgsiCmdInfo
from models.entity_properties_model import MeasureType
import pytest
import jobs.realtime.realtime_sync_job as rsj


class TestRealtimeSyncJob:
    @pytest.mark.parametrize(
        ("attr_value", "expected_type"),
        [
            ("string", MeasureType.STRING),
            (1, MeasureType.DOUBLE),
            (1.0, MeasureType.DOUBLE),
            (True, MeasureType.BOOL),
            (False, MeasureType.BOOL),
            (None, MeasureType.STRING),
            ("1", MeasureType.DOUBLE),
            ("true", MeasureType.BOOL),
            ("True", MeasureType.BOOL),
            ("False", MeasureType.BOOL),
            ("false", MeasureType.BOOL),
        ],
    )
    def test_get_attr_value_type(self, attr_value, expected_type):
        attr_value_type = rsj._get_attr_value_type(attr_value)

        assert attr_value_type == expected_type

    @pytest.mark.parametrize(
        ("entity_notification, entity_values"),
        [
            (
                EntityDataNotification(
                    urn="urn:ngsi-ld:Device:filling001",
                    tenant="tenant",
                    scope="scope",
                    type="SomeType",
                    db_id=1,
                    data=[
                        {
                            "name": "measure1",
                            "value": 1,
                            "type": "Property",
                            "units": None,
                            "timestamp": 1698647130,
                        },
                        {
                            "name": "measure2",
                            "value": 2.0,
                            "type": "Property",
                            "units": None,
                            "timestamp": 1698647131,
                        },
                        {
                            "name": "measure3",
                            "value": True,
                            "type": "Property",
                            "units": None,
                            "timestamp": 1698647132,
                        },
                        {
                            "name": "measure4",
                            "value": "string",
                            "type": "Property",
                            "units": None,
                            "timestamp": 1698647133,
                        },
                        {
                            "name": "measure5",
                            "value": "true",
                            "type": "Property",
                            "units": None,
                            "timestamp": 1698647134,
                        },
                        {
                            "name": "measure6",
                            "value": "33.0",
                            "type": "Property",
                            "units": None,
                            "timestamp": 1698647135,
                        },
                        {
                            "name": "measure7",
                            "value": "urn:false",
                            "type": "Relationship",
                            "units": None,
                            "timestamp": 1698647136,
                        },
                        {
                            "name": "measure8",
                            "value": {
                                "info": "info",
                                "status": "status",
                            },
                            "type": "Command",
                            "units": None,
                            "timestamp": 1698647137,
                        },
                        {
                            "name": "measure9",
                            "value": {
                                "info": {
                                    "sent": False,
                                    "value": "info",
                                },
                                "status": {"statusValue": "status"},
                            },
                            "type": "Command",
                            "units": None,
                            "timestamp": 1698647138,
                        },
                        {
                            "name": "measure10",
                            "value": '{ "info": { "sent": False, "value": "info", }, "status": {"statusValue": "status"}, }',
                            "type": "Command",
                            "units": None,
                            "timestamp": 1698647139,
                        },
                    ],
                ),
                [
                    {
                        "urn": "urn:ngsi-ld:Device:filling001",
                        "tenant": "tenant",
                        "scope": "scope",
                        "entity_id": 1,
                        "timestamp": datetime.datetime.fromtimestamp(1698647130),
                        "name": "measure1",
                        "value": 1,
                        "value_type": "double",
                        "type": "Property",
                        "units": None,
                        "timestamp_override": False,
                    },
                    {
                        "urn": "urn:ngsi-ld:Device:filling001",
                        "tenant": "tenant",
                        "scope": "scope",
                        "entity_id": 1,
                        "timestamp": datetime.datetime.fromtimestamp(1698647131),
                        "name": "measure2",
                        "value": 2.0,
                        "value_type": "double",
                        "type": "Property",
                        "units": None,
                        "timestamp_override": False,
                    },
                    {
                        "urn": "urn:ngsi-ld:Device:filling001",
                        "tenant": "tenant",
                        "scope": "scope",
                        "entity_id": 1,
                        "timestamp": datetime.datetime.fromtimestamp(1698647132),
                        "name": "measure3",
                        "value": True,
                        "value_type": "bool",
                        "type": "Property",
                        "units": None,
                        "timestamp_override": False,
                    },
                    {
                        "urn": "urn:ngsi-ld:Device:filling001",
                        "tenant": "tenant",
                        "scope": "scope",
                        "entity_id": 1,
                        "timestamp": datetime.datetime.fromtimestamp(1698647133),
                        "name": "measure4",
                        "value": "string",
                        "value_type": "string",
                        "type": "Property",
                        "units": None,
                        "timestamp_override": False,
                    },
                    {
                        "urn": "urn:ngsi-ld:Device:filling001",
                        "tenant": "tenant",
                        "scope": "scope",
                        "entity_id": 1,
                        "timestamp": datetime.datetime.fromtimestamp(1698647134),
                        "name": "measure5",
                        "value": "true",
                        "value_type": "bool",
                        "type": "Property",
                        "units": None,
                        "timestamp_override": False,
                    },
                    {
                        "urn": "urn:ngsi-ld:Device:filling001",
                        "tenant": "tenant",
                        "scope": "scope",
                        "entity_id": 1,
                        "timestamp": datetime.datetime.fromtimestamp(1698647135),
                        "name": "measure6",
                        "value": "33.0",
                        "value_type": "double",
                        "type": "Property",
                        "units": None,
                        "timestamp_override": False,
                    },
                    {
                        "urn": "urn:ngsi-ld:Device:filling001",
                        "tenant": "tenant",
                        "scope": "scope",
                        "entity_id": 1,
                        "timestamp": datetime.datetime.fromtimestamp(1698647136),
                        "name": "measure7",
                        "value": "urn:false",
                        "value_type": "string",
                        "type": "Relationship",
                        "units": None,
                        "timestamp_override": False,
                    },
                    {
                        "urn": "urn:ngsi-ld:Device:filling001",
                        "tenant": "tenant",
                        "scope": "scope",
                        "entity_id": 1,
                        "timestamp": datetime.datetime.fromtimestamp(1698647137),
                        "name": "measure8",
                        "value": {
                            "info": "info",
                            "status": "status",
                        },
                        "value_type": "string",
                        "type": "Command",
                        "units": None,
                        "timestamp_override": False,
                    },
                    {
                        "urn": "urn:ngsi-ld:Device:filling001",
                        "tenant": "tenant",
                        "scope": "scope",
                        "entity_id": 1,
                        "timestamp": datetime.datetime.fromtimestamp(1698647138),
                        "name": "measure9",
                        "value": {
                            "info": {
                                "sent": False,
                                "value": "info",
                            },
                            "status": {"statusValue": "status"},
                        },
                        "value_type": "string",
                        "type": "Command",
                        "units": None,
                        "timestamp_override": False,
                    },
                    {
                        "urn": "urn:ngsi-ld:Device:filling001",
                        "tenant": "tenant",
                        "scope": "scope",
                        "entity_id": 1,
                        "timestamp": datetime.datetime.fromtimestamp(1698647139),
                        "name": "measure10",
                        "value": '{ "info": { "sent": False, "value": "info", }, "status": {"statusValue": "status"}, }',
                        "value_type": "string",
                        "type": "Command",
                        "units": None,
                        "timestamp_override": False,
                    },
                ],
            ),
        ],
    )
    def test_EntityNotificationData_to_EntityValues(
        self, entity_notification: EntityDataNotification, entity_values: List[dict]
    ):
        converted_entity_values = rsj._EntityNotificationData_to_EntityValues(
            entity_notification
        )

        assert len(converted_entity_values) == len(entity_values)

        for i in range(len(converted_entity_values)):
            assert converted_entity_values[i] == entity_values[i]

    @pytest.mark.parametrize(
        ("cmd", "expected_pending", "expected_pending_value"),
        [
            (
                NgsiCmdInfo(
                    entity_urn="urn:ngsi-ld:Device:filling001",
                    entity_tenant="tenant",
                    entity_scope="scope",
                    entity_type="LibeliumOne",
                    cmd_name="cmd1",
                    cmd_info={"status": "PENDING", "value": "value"},
                    cmd_status="OK, this wont be used",
                    ts_cmd_info=datetime.datetime.fromtimestamp(1698647130),
                    ts_cmd_status=datetime.datetime.fromtimestamp(1698647130),
                ),
                True,
                "value",
            ),
            (
                NgsiCmdInfo(
                    entity_urn="urn:ngsi-ld:Device:filling001",
                    entity_tenant="tenant",
                    entity_scope="scope",
                    entity_type="LibeliumOne",
                    cmd_name="cmd1",
                    cmd_info={"status": "PENDING", "value": 33},
                    cmd_status="OK, this wont be used",
                    ts_cmd_info=datetime.datetime.fromtimestamp(1698647130),
                    ts_cmd_status=datetime.datetime.fromtimestamp(1698647130),
                ),
                True,
                33,
            ),
            (
                NgsiCmdInfo(
                    entity_urn="urn:ngsi-ld:Device:filling001",
                    entity_tenant="tenant",
                    entity_scope="scope",
                    entity_type="LibeliumOne",
                    cmd_name="cmd1",
                    cmd_info={"status": "SENT", "value": 33},
                    cmd_status="OK, this wont be used",
                    ts_cmd_info=datetime.datetime.fromtimestamp(1698647130),
                    ts_cmd_status=datetime.datetime.fromtimestamp(1698647130),
                ),
                False,
                33,
            ),
            (
                NgsiCmdInfo(
                    entity_urn="urn:ngsi-ld:Device:filling001",
                    entity_tenant="tenant",
                    entity_scope="scope",
                    entity_type="LibeliumOne",
                    cmd_name="cmd1",
                    cmd_info={"status": "SENT", "value": [33]},
                    cmd_status="OK, this wont be used",
                    ts_cmd_info=datetime.datetime.fromtimestamp(1698647130),
                    ts_cmd_status=datetime.datetime.fromtimestamp(1698647130),
                ),
                False,
                [33],
            ),
            (
                NgsiCmdInfo(
                    entity_urn="urn:ngsi-ld:Device:filling001",
                    entity_tenant="tenant",
                    entity_scope="scope",
                    entity_type="LibeliumOne",
                    cmd_name="cmd1",
                    cmd_info={"status": "SENT"},
                    cmd_status="OK, this wont be used",
                    ts_cmd_info=datetime.datetime.fromtimestamp(1698647130),
                    ts_cmd_status=datetime.datetime.fromtimestamp(1698647130),
                ),
                False,
                None,
            ),
            (
                NgsiCmdInfo(
                    entity_urn="urn:ngsi-ld:Device:filling001",
                    entity_tenant="tenant",
                    entity_scope="scope",
                    entity_type="LibeliumOne",
                    cmd_name="cmd1",
                    cmd_info={},
                    cmd_status="OK, this wont be used",
                    ts_cmd_info=datetime.datetime.fromtimestamp(1698647130),
                    ts_cmd_status=datetime.datetime.fromtimestamp(1698647130),
                ),
                False,
                None,
            ),
        ],
    )
    def test_cmd_status_interpreter(
        self, cmd: NgsiCmdInfo, expected_pending: bool, expected_pending_value: Any
    ):

        factory = CmdStatusInterpreterFactory()

        interpreter = factory.build_interpreter(cmd.entity_type)

        assert interpreter is not None

        is_pending, pending_value = interpreter.interpret_status(cmd)

        assert is_pending == expected_pending
        assert pending_value == expected_pending_value
