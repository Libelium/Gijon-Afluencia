"""Pruebas de los conectores de foto periodica: aforos, desplazamientos e inventario."""

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import models.crud.crud_entity_properties as crud_entity_properties
import models.crud.crud_out_connectors as crud_out_connectors
import tasks.out_connectors as out_connector_tasks
from jobs.out_connectors.out_connector import mqtt as mqtt_connector
from jobs.out_connectors.out_connector.payload.device_inventory import (
    DeviceInventoryPayloadBuilder,
)
from jobs.out_connectors.out_connector.payload.flow_readings import (
    FlowReadingsPayloadBuilder,
)
from jobs.out_connectors.out_connector.payload.occupancy_readings import (
    OccupancyReadingsPayloadBuilder,
)
from jobs.out_connectors.out_connector.payload.snapshot_base import SnapshotPayloadBuilder

WINDOW = datetime(2026, 10, 26, 10, 0, tzinfo=timezone.utc)


def prop(entity_id, urn, name, value, timestamp=WINDOW):
    """Fila de entity_properties: el valor siempre como texto."""
    return SimpleNamespace(
        entity_id=entity_id, urn=urn, name=name, value=str(value), timestamp=timestamp
    )


def realtime(mocker, rows):
    """
    Base de tiempo real simulada: filtra las filas como lo harian las consultas.
    """
    mocker.patch.object(
        crud_entity_properties,
        "get_entity_properties",
        side_effect=lambda ids, names, db: [
            r for r in rows if r.entity_id in ids and r.name in names
        ],
    )
    mocker.patch.object(
        crud_entity_properties,
        "get_entity_properties_by_urn",
        side_effect=lambda urns, name, db: [
            r for r in rows if r.urn in urns and r.name == name
        ],
    )
    mocker.patch.object(
        crud_entity_properties,
        "get_entity_ids_with_property_value",
        side_effect=lambda name, values, db: sorted(
            {r.entity_id for r in rows if r.name == name and r.value in values}
        ),
    )


def zones_db(zone_ids):
    """Base de datos principal simulada: solo esas entidades son CrowdFlowZone."""
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.all.return_value = [
        (i,) for i in zone_ids
    ]
    return db


def linked(mocker, entities=(), devices=()):
    mocker.patch.object(
        crud_out_connectors,
        "get_linked_model_ids",
        side_effect=lambda connector_id, model_type, db: list(
            entities if model_type == "entities" else devices
        ),
    )


# ---------------------------------------------------------------------------
# Utilidades comunes
# ---------------------------------------------------------------------------


class TestSnapshotHelpers:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc), "2026-10-26T12:00:00Z"),
            ("2026-10-26T12:00:00+02:00", "2026-10-26T10:00:00Z"),
            ("2026-10-26T10:00:00Z", "2026-10-26T10:00:00Z"),
            (datetime(2026, 10, 26, 10, 0), "2026-10-26T10:00:00Z"),
            (None, None),
        ],
    )
    def test_dates_go_out_in_utc(self, value, expected):
        assert SnapshotPayloadBuilder.iso_utc(value) == expected

    @pytest.mark.parametrize(
        "value, expected", [("12.0", 12), ("12.5", 12.5), ("abc", None), (None, None)]
    )
    def test_numbers_come_from_text(self, value, expected):
        assert SnapshotPayloadBuilder.number(value) == expected


# ---------------------------------------------------------------------------
# Aforos
# ---------------------------------------------------------------------------


class TestOccupancyReadings:
    def test_one_reading_per_linked_zone(self, mocker):
        linked(mocker, entities=[1, 2, 3])
        realtime(
            mocker,
            [
                prop(1, "urn:ngsi-ld:CrowdFlowZone:playa", "occupancy", 120.0),
                prop(1, "urn:ngsi-ld:CrowdFlowZone:playa", "name", "Playa"),
                prop(2, "urn:ngsi-ld:CrowdFlowZone:puerto", "occupancy", 7),
                # Zona sin dato de ocupacion todavia: no se envia.
                prop(3, "urn:ngsi-ld:CrowdFlowZone:parque", "name", "Parque"),
            ],
        )

        payload = OccupancyReadingsPayloadBuilder(1, zones_db([1, 2, 3]), MagicMock()).build_payload()

        assert payload == {
            "lecturas": [
                {
                    "dpa": {
                        "fechaLectura": "2026-10-26T10:00:00Z",
                        "idPuntoInteres": "playa",
                        "descripcionPuntoInteres": "Playa",
                        "total": 120,
                    }
                },
                {
                    "dpa": {
                        "fechaLectura": "2026-10-26T10:00:00Z",
                        "idPuntoInteres": "puerto",
                        "descripcionPuntoInteres": "puerto",
                        "total": 7,
                    }
                },
            ]
        }

    def test_nothing_linked_sends_nothing(self, mocker):
        linked(mocker)
        realtime(mocker, [])

        assert OccupancyReadingsPayloadBuilder(1, MagicMock(), MagicMock()).build_payload() is None

    def test_only_zones_are_points_of_interest(self, mocker):
        # La 9 es una observacion de Smart Spot asociada al conector: tambien tiene occupancy.
        linked(mocker, entities=[1, 9])
        realtime(
            mocker,
            [
                prop(1, "urn:ngsi-ld:CrowdFlowZone:playa", "occupancy", 120),
                prop(9, "urn:ngsi-ld:CrowdFlowObserved:PRUEBA-DATO-001", "occupancy", 0.9),
            ],
        )

        payload = OccupancyReadingsPayloadBuilder(1, zones_db([1]), MagicMock()).build_payload()

        assert [r["dpa"]["idPuntoInteres"] for r in payload["lecturas"]] == ["playa"]

    def test_zone_query_filters_by_datamodel(self, mocker):
        from sqlalchemy.dialects import postgresql
        from sqlalchemy.orm import Query, Session

        linked(mocker, entities=[1, 9])
        captured = []
        mocker.patch.object(Query, "all", lambda query: captured.append(query) or [])

        OccupancyReadingsPayloadBuilder(1, Session(), MagicMock()).linked_zone_ids()

        sql = str(captured[0].statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        ))
        assert "entities.datamodel = 'CrowdFlowZone'" in sql


# ---------------------------------------------------------------------------
# Desplazamientos
# ---------------------------------------------------------------------------


def flow(entity_id, origin, destination, count, start="2026-10-26T10:00:00+00:00"):
    urn = f"urn:ngsi-ld:CrowdFlowEventETL:{entity_id}"
    return [
        prop(entity_id, urn, "origin", origin),
        prop(entity_id, urn, "destination", destination),
        prop(entity_id, urn, "count", count),
        prop(entity_id, urn, "startDate", start),
    ]


class TestFlowReadings:
    A, B, C = (f"urn:ngsi-ld:Device:smsp00{i}" for i in (1, 2, 3))

    def build(self, mocker, rows, sensors):
        mocker.patch.object(
            FlowReadingsPayloadBuilder,
            "_FlowReadingsPayloadBuilder__linked_sensor_urns",
            return_value=sensors,
        )
        realtime(mocker, rows)
        return FlowReadingsPayloadBuilder(1, MagicMock(), MagicMock()).build_payload()

    def test_share_is_over_everything_that_left_the_origin(self, mocker):
        rows = (
            flow(10, self.A, self.B, 30)
            + flow(11, self.A, self.C, 10)
            + flow(12, self.C, self.B, 5)
            + [prop(1, self.A, "name", "Playa"), prop(2, self.B, "name", "Puerto")]
        )

        # Solo B esta asociado: A -> C cuenta para el total de A aunque no se envie.
        payload = self.build(mocker, rows, [self.B])

        assert payload["lecturas"] == [
            {
                "dpa": {
                    "fechaLectura": "2026-10-26T10:00:00Z",
                    "idOrigen": "smsp001",
                    "descripcionOrigen": "Playa",
                    "idDestino": "smsp002",
                    "descripcionDestino": "Puerto",
                    "total(%)": 75.0,
                }
            },
            {
                "dpa": {
                    "fechaLectura": "2026-10-26T10:00:00Z",
                    "idOrigen": "smsp003",
                    "descripcionOrigen": "smsp003",
                    "idDestino": "smsp002",
                    "descripcionDestino": "Puerto",
                    "total(%)": 100.0,
                }
            },
        ]

    def test_only_the_last_window_is_sent(self, mocker):
        rows = flow(10, self.A, self.B, 30) + flow(
            11, self.A, self.C, 10, start="2026-10-26T09:00:00+00:00"
        )

        payload = self.build(mocker, rows, [self.A])

        assert [r["dpa"]["idDestino"] for r in payload["lecturas"]] == ["smsp002"]
        assert payload["lecturas"][0]["dpa"]["total(%)"] == 100.0

    def test_per_sensor_aggregates_are_not_movements(self, mocker):
        payload = self.build(mocker, flow(10, self.A, self.A, 30), [self.A])

        assert payload is None


# ---------------------------------------------------------------------------
# Inventario
# ---------------------------------------------------------------------------


class TestDeviceInventory:
    def test_describes_each_device_with_its_main_entity(self, mocker):
        linked(mocker, devices=[5])
        realtime(mocker, [prop(50, "urn:ngsi-ld:Device:smsp005", "name", "Sensor playa")])
        mocker.patch.object(
            crud_entity_properties,
            "get_entity_location",
            return_value={"type": "Point", "coordinates": [-5.66, 43.54]},
        )
        device = SimpleNamespace(
            id=5, name="Activo playa", description="Entrada norte", serial="SER-5"
        )
        device_type = SimpleNamespace(name="Smart Spot", category="Afluencia")
        iris_db = MagicMock()
        iris_db.query.return_value.outerjoin.return_value.filter.return_value.order_by.return_value.all.return_value = [
            (device, device_type)
        ]
        mocker.patch.object(
            DeviceInventoryPayloadBuilder,
            "_DeviceInventoryPayloadBuilder__main_entities",
            return_value={5: SimpleNamespace(id=50, urn="urn:ngsi-ld:Device:smsp005")},
        )

        payload = DeviceInventoryPayloadBuilder(1, iris_db, MagicMock()).build_payload()

        assert payload == {
            "devices": [
                {
                    "general": {
                        "nombreSensor": "Sensor playa",
                        "idSensor": "urn:ngsi-ld:Device:smsp005",
                        "coordenadas": {"lat": 43.54, "lon": -5.66},
                        "nombre": "Activo playa",
                        "modelo": "Smart Spot",
                        "familia": "Afluencia",
                        "descripcion": "Entrada norte",
                        "numeroSerie": "SER-5",
                    },
                    "groupings": [],
                }
            ]
        }

    def test_nothing_linked_sends_nothing(self, mocker):
        linked(mocker)

        assert DeviceInventoryPayloadBuilder(1, MagicMock(), MagicMock()).build_payload() is None


# ---------------------------------------------------------------------------
# Publicacion y programacion
# ---------------------------------------------------------------------------


def snapshot_model(**overrides):
    values = {
        "id": 1,
        "ipAddress": "broker.example.org",
        "port": 8883,
        "username": None,
        "password": None,
        "clientId": "pid-test",
        "ssl": False,
        "sslCert": None,
        "clientCert": None,
        "clientKey": None,
        "topicTemplate": [{"type": "static", "value": "plataforma/aforos"}],
        "payload_type": "occupancy_readings",
        "payload_config": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class TestSnapshotPublishing:
    @pytest.fixture
    def client(self, mocker):
        from paho.mqtt.packettypes import PacketTypes
        from paho.mqtt.reasoncodes import ReasonCode

        mocker.patch.object(mqtt_connector.settings, "MQTT_ALLOWED_DESTINATIONS", "example.org")
        mocker.patch(
            "jobs.alarms.action.senders.socket.getaddrinfo",
            return_value=[(None, None, None, None, ("93.184.216.34", 0))],
        )
        client = MagicMock()
        client.loop_start.side_effect = lambda: client.on_connect(
            client, None, None, ReasonCode(PacketTypes.CONNACK, identifier=0), None
        )
        mocker.patch.object(mqtt_connector.mqtt, "Client", return_value=client)
        return client

    def snapshot(self, mocker, payload):
        mocker.patch.object(mqtt_connector, "get_snapshot_builder").return_value.build_payload.return_value = payload

    def test_publishes_every_reading_in_one_message(self, mocker, client):
        payload = {"lecturas": [{"dpa": {"total": 1}}, {"dpa": {"total": 2}}]}
        self.snapshot(mocker, payload)

        sent = mqtt_connector.MqttConnector(1, snapshot_model(), None, MagicMock()).handle()

        assert sent is True
        client.publish.assert_called_once_with("plataforma/aforos", json.dumps(payload), qos=1)

    def test_empty_snapshot_does_not_connect(self, mocker, client):
        self.snapshot(mocker, None)

        sent = mqtt_connector.MqttConnector(1, snapshot_model(), None, MagicMock()).handle()

        assert sent is False
        client.connect.assert_not_called()

    def test_snapshot_topic_cannot_take_variables(self, mocker, client):
        self.snapshot(mocker, {"lecturas": []})
        model = snapshot_model(topicTemplate=[{"type": "variable", "value": "urn"}])

        with pytest.raises(ValueError):
            mqtt_connector.MqttConnector(1, model, None, MagicMock()).handle()

    def test_notification_formats_need_a_notification(self, client):
        with pytest.raises(ValueError):
            mqtt_connector.MqttConnector(
                1, snapshot_model(payload_type="key_value"), None, MagicMock()
            ).handle()

    def test_periodic_task_enqueues_one_job_per_connector(self, mocker):
        mocker.patch.object(out_connector_tasks, "main_session").return_value.__enter__.return_value = MagicMock()
        mocker.patch.object(
            crud_out_connectors, "get_active_snapshot_connector_ids", return_value=[3, 4]
        )
        delay = mocker.patch.object(out_connector_tasks.snapshot_connector_job, "delay")

        out_connector_tasks.snapshot_connectors_job(["occupancy_readings"])

        assert [c.args for c in delay.call_args_list] == [(3,), (4,)]
