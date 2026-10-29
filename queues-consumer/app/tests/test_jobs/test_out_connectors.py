"""Pruebas del conector de salida MQTT: destino, topic, publicacion y salud del conector."""

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import paho.mqtt.client as mqtt
import pytest
from paho.mqtt.reasoncodes import ReasonCode
from paho.mqtt.packettypes import PacketTypes

import models.crud.crud_out_connectors as crud_out_connectors
from jobs.alarms.action.senders import DestinationNotAllowed
from jobs.out_connectors import out_connector_job
from jobs.out_connectors.out_connector import mqtt as mqtt_connector
from jobs.out_connectors.out_connector.factory.out_connector_factory import (
    OutConnectorFactory,
)
from jobs.out_connectors.out_connector.factory.payload_factory import PayloadFactory
from jobs.out_connectors.out_connector.payload import legacy
from jobs.out_connectors.out_connector_job import OutConnectorJob
from jobs.sync.entity_sync import EntitySync
from schemas.entity_data_notification import EntityAttr, EntityDataNotification


@pytest.fixture
def entity_data():
    return EntityDataNotification(
        urn="urn:ngsi-ld:Device:smsp001",
        tenant="pid_gijon",
        scope="/",
        type="Device",
        db_id=7,
        devices=[3],
        data=[
            EntityAttr(name="r_cfo_countm", value=12, type="Property", timestamp=1700000000),
        ],
    )


def mqtt_model(**overrides):
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
        "topicTemplate": [
            {"type": "static", "value": "pid/"},
            {"type": "variable", "value": "tenant"},
            {"type": "static", "value": "/"},
            {"type": "variable", "value": "urn"},
        ],
        "payload_type": "key_value",
        "payload_config": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def allow_brokers(mocker, value="example.org", resolves_to="93.184.216.34"):
    mocker.patch.object(mqtt_connector.settings, "MQTT_ALLOWED_DESTINATIONS", value)
    mocker.patch(
        "jobs.alarms.action.senders.socket.getaddrinfo",
        return_value=[(None, None, None, None, (resolves_to, 0))],
    )


def fake_client(mocker, reason_code=0, published=True):
    """
    Cliente paho simulado: loop_start() responde al CONNECT como lo haria el broker.
    """
    client = MagicMock()

    def loop_start():
        client.on_connect(client, None, None, ReasonCode(PacketTypes.CONNACK, identifier=reason_code), None)

    client.loop_start.side_effect = loop_start
    client.publish.return_value.is_published.return_value = published
    mocker.patch.object(mqtt_connector.mqtt, "Client", return_value=client)
    mocker.patch.object(mqtt_connector, "PayloadFactory").return_value.get_payload_builder.return_value.build_payload.return_value = {"id": "x"}
    return client


# ---------------------------------------------------------------------------
# Destino del broker
# ---------------------------------------------------------------------------


class TestBrokerDestination:
    def test_empty_allow_list_sends_nothing(self, mocker):
        mocker.patch.object(mqtt_connector.settings, "MQTT_ALLOWED_DESTINATIONS", "")

        with pytest.raises(DestinationNotAllowed):
            mqtt_connector.check_broker_destination("broker.example.org")

    def test_host_outside_the_list_is_refused(self, mocker):
        allow_brokers(mocker)

        with pytest.raises(DestinationNotAllowed):
            mqtt_connector.check_broker_destination("example.org.attacker.tld")

    def test_subdomain_of_an_allowed_host_passes(self, mocker):
        allow_brokers(mocker)

        mqtt_connector.check_broker_destination("Broker.Example.org")

    def test_allowed_host_resolving_to_an_internal_address_is_refused(self, mocker):
        allow_brokers(mocker, resolves_to="10.0.0.5")

        with pytest.raises(DestinationNotAllowed):
            mqtt_connector.check_broker_destination("broker.example.org")


# ---------------------------------------------------------------------------
# Publicacion
# ---------------------------------------------------------------------------


class TestMqttConnector:
    def test_publishes_the_payload_to_the_built_topic(self, mocker, entity_data):
        allow_brokers(mocker)
        client = fake_client(mocker)

        mqtt_connector.MqttConnector(1, mqtt_model(), entity_data, MagicMock()).handle()

        client.connect.assert_called_once_with("broker.example.org", 8883)
        client.publish.assert_called_once_with(
            "pid/pid_gijon/urn:ngsi-ld:Device:smsp001", '{"id": "x"}', qos=1
        )
        client.publish.return_value.wait_for_publish.assert_called_once()
        client.disconnect.assert_called_once()
        client.loop_stop.assert_called_once()

    def test_sets_credentials_only_when_both_are_given(self, mocker, entity_data):
        allow_brokers(mocker)
        client = fake_client(mocker)

        mqtt_connector.MqttConnector(
            1, mqtt_model(username="user", password="secret"), entity_data, MagicMock()
        ).handle()

        client.username_pw_set.assert_called_once_with("user", "secret")

    def test_refused_connection_raises_and_disconnects(self, mocker, entity_data):
        allow_brokers(mocker)
        # 0x87: Not authorized
        client = fake_client(mocker, reason_code=0x87)

        with pytest.raises(ConnectionError):
            mqtt_connector.MqttConnector(1, mqtt_model(), entity_data, MagicMock()).handle()

        client.publish.assert_not_called()
        client.disconnect.assert_called_once()

    def test_unconfirmed_publish_raises(self, mocker, entity_data):
        allow_brokers(mocker)
        fake_client(mocker, published=False)

        with pytest.raises(TimeoutError):
            mqtt_connector.MqttConnector(1, mqtt_model(), entity_data, MagicMock()).handle()

    def test_refused_destination_never_connects(self, mocker, entity_data):
        mocker.patch.object(mqtt_connector.settings, "MQTT_ALLOWED_DESTINATIONS", "")
        client = fake_client(mocker)

        with pytest.raises(DestinationNotAllowed):
            mqtt_connector.MqttConnector(1, mqtt_model(), entity_data, MagicMock()).handle()

        client.connect.assert_not_called()

    def test_legacy_publishes_one_message_per_attribute(self, mocker, entity_data):
        allow_brokers(mocker)
        client = fake_client(mocker)
        mqtt_connector.PayloadFactory.return_value.get_payload_builder.return_value.build_payload.return_value = [
            {"value": 12},
            {"value": 3},
        ]
        entity_data.data.append(
            EntityAttr(name="r_cfe_block", value=3, type="Property", timestamp=1700000000)
        )
        model = mqtt_model(
            payload_type="legacy",
            topicTemplate=[
                {"type": "static", "value": "pid/"},
                {"type": "variable", "value": "measure"},
            ],
        )

        mqtt_connector.MqttConnector(1, model, entity_data, MagicMock()).handle()

        client.connect.assert_called_once()
        assert [c.args for c in client.publish.call_args_list] == [
            ("pid/r_cfo_countm", '{"value": 12}'),
            ("pid/r_cfe_block", '{"value": 3}'),
        ]

    def test_unknown_topic_variable_is_an_error(self, mocker, entity_data):
        allow_brokers(mocker)
        fake_client(mocker)
        model = mqtt_model(topicTemplate=[{"type": "variable", "value": "measure"}])

        with pytest.raises(ValueError):
            mqtt_connector.MqttConnector(1, model, entity_data, MagicMock()).handle()

    def test_client_certificate_is_loaded_from_private_temporary_files(self, mocker, entity_data):
        allow_brokers(mocker)
        client = fake_client(mocker)
        context = mocker.patch.object(mqtt_connector.ssl, "create_default_context").return_value
        seen = {}

        def load_cert_chain(certfile, keyfile):
            for name, path in (("cert", certfile), ("key", keyfile)):
                seen[name] = (open(path).read(), oct(os.stat(path).st_mode & 0o777), path)

        context.load_cert_chain.side_effect = load_cert_chain
        model = mqtt_model(
            ssl=True,
            clientCert="-----BEGIN CERTIFICATE-----\nCERT\n-----END CERTIFICATE-----",
            clientKey="-----BEGIN RSA PRIVATE KEY-----\nKEY\n-----END RSA PRIVATE KEY-----",
        )

        mqtt_connector.MqttConnector(1, model, entity_data, MagicMock()).handle()

        assert seen["cert"][0] == model.clientCert and seen["key"][0] == model.clientKey
        assert seen["cert"][1] == seen["key"][1] == "0o600"
        # Ya cargados, los ficheros no se quedan en disco.
        assert not os.path.exists(seen["cert"][2]) and not os.path.exists(seen["key"][2])
        client.tls_set_context.assert_called_once_with(context)

    def test_client_certificate_without_key_is_an_error(self, mocker, entity_data):
        allow_brokers(mocker)
        client = fake_client(mocker)
        model = mqtt_model(ssl=True, clientCert="-----BEGIN CERTIFICATE-----", clientKey=None)

        with pytest.raises(ValueError):
            mqtt_connector.MqttConnector(1, model, entity_data, MagicMock()).handle()

        client.connect.assert_not_called()

    def test_client_certificate_without_tls_is_an_error(self, mocker, entity_data):
        allow_brokers(mocker)
        fake_client(mocker)
        model = mqtt_model(ssl=False, clientCert="-----BEGIN CERTIFICATE-----", clientKey="k")

        with pytest.raises(ValueError):
            mqtt_connector.MqttConnector(1, model, entity_data, MagicMock()).handle()

    def test_refused_message_reports_the_broker_reason(self, mocker, entity_data):
        allow_brokers(mocker)
        client = fake_client(mocker)
        info = MagicMock(mid=7)
        info.is_published.return_value = True

        def publish(topic, message, qos):
            # Como paho: primero el callback con el motivo del PUBACK, luego publicado.
            client.on_publish(client, None, 7, ReasonCode(PacketTypes.PUBACK, identifier=0x87), None)
            return info

        client.publish.side_effect = publish

        with pytest.raises(ConnectionError, match="Not authorized"):
            mqtt_connector.MqttConnector(1, mqtt_model(), entity_data, MagicMock()).handle()

        client.disconnect.assert_called_once()

    def test_client_uses_the_paho_v2_callback_api(self, entity_data):
        client = mqtt_connector.MqttConnector(
            1, mqtt_model(), entity_data, MagicMock()
        )._MqttConnector__create_client()

        assert isinstance(client, mqtt.Client)
        assert client.protocol == mqtt.MQTTv5
        assert client.connect_timeout == mqtt_connector.settings.OUT_CONNECTOR_REQUEST_TIMEOUT


# ---------------------------------------------------------------------------
# Factorias
# ---------------------------------------------------------------------------


class TestFactories:
    def test_unsupported_payload_type_raises(self):
        with pytest.raises(ValueError):
            PayloadFactory().get_payload_builder(
                mqtt_model(payload_type="custom"), MagicMock()
            )

    def test_legacy_payload_follows_the_payload_config(self, mocker, entity_data):
        mocker.patch.object(legacy, "get_units_bulk", return_value={"r_cfo_countm": "people"})
        mocker.patch.object(legacy.crud_devices, "get_device_serial", return_value="SN1")
        mocker.patch.object(legacy.crud_devices, "get_device_case_id", return_value=None)
        model = mqtt_model(
            payload_type="legacy",
            payload_config=[
                {"key": "value", "value": "v", "active": True},
                {"key": "unit", "value": "u", "active": True},
                {"key": "urn", "value": "id", "active": False},
            ],
        )

        builder = PayloadFactory().get_payload_builder(model, MagicMock())

        assert builder.build_payload(entity_data) == [{"v": 12, "u": "people", "serial": "SN1"}]

    def test_legacy_payload_without_config_sends_every_field(self, mocker, entity_data):
        mocker.patch.object(legacy, "get_units_bulk", return_value={})
        entity_data.devices = []

        builder = PayloadFactory().get_payload_builder(
            mqtt_model(payload_type="legacy", payload_config=[]), MagicMock()
        )
        message = builder.build_payload(entity_data)[0]

        assert set(message) == {"timestamp", "value", "urn", "tenant", "scope", "measure", "unit"}
        assert message["measure"] == "r_cfo_countm"

    def test_unsupported_connector_type_raises(self, entity_data):
        out_connector = SimpleNamespace(id=1, connectable_type="http_connector")

        with pytest.raises(ValueError):
            OutConnectorFactory().build_out_connector(out_connector, entity_data, MagicMock())

    def test_builds_the_mqtt_connector(self, mocker, entity_data):
        mocker.patch.object(crud_out_connectors, "get_mqtt_connector", return_value=mqtt_model())
        out_connector = SimpleNamespace(
            id=1, connectable_type="mqtt_connector", connectable_id=1, use_readable_names=None
        )

        connector = OutConnectorFactory().build_out_connector(
            out_connector, entity_data, MagicMock()
        )

        assert isinstance(connector, mqtt_connector.MqttConnector)


# ---------------------------------------------------------------------------
# Job: reintentos y desactivacion
# ---------------------------------------------------------------------------


def stored_connector(**overrides):
    values = {
        "id": 1,
        "type": "mqtt",
        "status": "active",
        "retries": 0,
        "last_connection": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture
def crud(mocker):
    mocker.patch.object(out_connector_job, "create_error_log")
    return mocker.patch.object(out_connector_job, "crud_out_connectors")


def run_job(mocker, entity_data, fails=False, sent=True):
    connector = MagicMock()
    connector.handle.return_value = sent
    if fails:
        connector.handle.side_effect = ConnectionError("broker down")
    mocker.patch.object(
        OutConnectorFactory, "build_out_connector", return_value=connector
    )
    OutConnectorJob(
        out_connector_id=1, notification=entity_data, db=MagicMock(), realtime_db=MagicMock()
    ).handle()
    return connector


class TestOutConnectorJob:
    def test_nothing_to_send_leaves_the_health_alone(self, mocker, crud, entity_data):
        crud.get_out_connector_by_id.return_value = stored_connector(retries=2)

        run_job(mocker, entity_data, sent=False)

        crud.update_out_connector.assert_not_called()
        crud.update_out_connector_last_connection_if_newer.assert_not_called()
        crud.update_out_connector_retries.assert_not_called()

    def test_inactive_connector_is_skipped(self, mocker, crud, entity_data):
        crud.get_out_connector_by_id.return_value = stored_connector(status="inactive")

        connector = run_job(mocker, entity_data)

        connector.handle.assert_not_called()

    def test_success_records_the_connection(self, mocker, crud, entity_data):
        crud.get_out_connector_by_id.return_value = stored_connector()

        run_job(mocker, entity_data)

        crud.update_out_connector_last_connection_if_newer.assert_called_once()
        crud.update_out_connector.assert_not_called()

    def test_success_after_failures_resets_retries(self, mocker, crud, entity_data):
        crud.get_out_connector_by_id.return_value = stored_connector(retries=3)

        run_job(mocker, entity_data)

        crud.update_out_connector.assert_called_once_with(1, {"retries": 0}, mocker.ANY)

    def test_failure_below_the_limit_only_counts(self, mocker, crud, entity_data):
        crud.get_out_connector_by_id.side_effect = [
            stored_connector(retries=0),
            stored_connector(retries=1),
        ]

        run_job(mocker, entity_data, fails=True)

        crud.update_out_connector_retries.assert_called_once()
        crud.update_out_connector.assert_not_called()

    def test_failure_at_the_limit_deactivates(self, mocker, crud, entity_data):
        # As Postgres returns it: naive, in UTC.
        old_success = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        crud.get_out_connector_by_id.side_effect = [
            stored_connector(retries=4),
            stored_connector(retries=5, last_connection=old_success),
        ]
        mocker.patch.object(out_connector_job.settings, "NUM_MAX_RETRIES", 5)

        run_job(mocker, entity_data, fails=True)

        crud.update_out_connector.assert_called_once_with(
            1, {"status": "inactive", "retries": 0}, mocker.ANY
        )

    def test_recent_success_keeps_the_connector_active(self, mocker, crud, entity_data):
        recent_success = datetime.now(timezone.utc) - timedelta(seconds=5)
        crud.get_out_connector_by_id.side_effect = [
            stored_connector(retries=4),
            stored_connector(retries=5, last_connection=recent_success),
        ]
        mocker.patch.object(out_connector_job.settings, "NUM_MAX_RETRIES", 5)
        mocker.patch.object(
            out_connector_job.settings, "CONNECTOR_DEACTIVATION_WINDOW_SECONDS", 60
        )

        run_job(mocker, entity_data, fails=True)

        crud.update_out_connector.assert_not_called()


# ---------------------------------------------------------------------------
# Observer de la ingesta y consulta de conectores
# ---------------------------------------------------------------------------


class TestCheckConnectors:
    def test_enqueues_one_job_per_connector(self, mocker, entity_data):
        connectors = [MagicMock(), MagicMock()]
        for i, connector in enumerate(connectors):
            connector.dict.return_value = {"id": i}
        mocker.patch.object(
            crud_out_connectors, "get_related_out_connectors", return_value=connectors
        )
        delay = mocker.patch("tasks.out_connectors.generic_connector_job.delay")

        sync = EntitySync(payload=MagicMock(), db=MagicMock(), realtime_db=MagicMock())
        sync.db = MagicMock()
        sync.check_connectors(entity_data)

        assert delay.call_count == 2
        request = delay.call_args_list[0].args[0]
        assert request.out_connector == {"id": 0}
        assert request.notification.urn == entity_data.urn

    def test_no_filters_returns_nothing_without_querying(self):
        db = MagicMock()

        assert crud_out_connectors.get_related_out_connectors([], [], db) == []
        db.query.assert_not_called()
