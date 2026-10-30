import json
import os
import re
import ssl
import tempfile
import threading
import uuid
from typing import List, Optional, Tuple

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session

from config.config import settings
from jobs.alarms.action.senders import DestinationNotAllowed, _reject_internal_host
from jobs.out_connectors.out_connector.factory.payload_factory import (
    PayloadFactory,
    get_snapshot_builder,
)
from jobs.out_connectors.out_connector.out_connector import OutConnector
from models.out_connector_mqtt_model import (
    MqttConnector as MqttConnectorModel,
    SNAPSHOT_PAYLOAD_TYPES,
)
from schemas.entity_data_notification import EntityDataNotification


# Topic variable of the snapshots that sends one message per item.
ID_VARIABLE = "id"


def topic_level(value: str) -> str:
    """
    A value as a single topic level: "/" would open more levels, and "#" and "+" are
    subscription wildcards a publish topic cannot carry.
    """
    return re.sub(r"[/#+]", "_", str(value))


class MqttConnector(OutConnector):
    """
    Publishes to an MQTT broker with the payload format and topic the connector has
    configured: one message per notification (per attribute in legacy) or, for the
    snapshot payload types, one message with every reading of the linked models.
    """

    def __init__(
        self,
        out_connector_id: int,
        connector: MqttConnectorModel,
        entity_data: Optional[EntityDataNotification],
        iris_db: Session,
        use_readable_names: bool = False,
        realtime_db: Optional[Session] = None,
    ):
        self.out_connector_id = out_connector_id
        self.connector = connector
        self.entity_data = entity_data
        self.iris_db = iris_db
        self.use_readable_names = use_readable_names
        self.realtime_db = realtime_db

    def handle(self) -> bool:
        check_broker_destination(self.connector.ipAddress)

        if self.connector.payload_type in SNAPSHOT_PAYLOAD_TYPES:
            publishes = self.__snapshot_publishes()
        else:
            publishes = self.__notification_publishes()

        if not publishes:
            return False

        self.__publish(publishes)
        return True

    def __notification_publishes(self) -> List[Tuple[str, str]]:
        if self.entity_data is None:
            raise ValueError(
                f"Payload type {self.connector.payload_type!r} is sent per notification"
            )

        payload_builder = PayloadFactory().get_payload_builder(
            self.connector, self.iris_db, self.use_readable_names
        )
        payload = payload_builder.build_payload(self.entity_data)

        if self.connector.payload_type == "legacy":
            # One message per attribute, each to its own topic
            return [
                (self.__build_topic(attr.name), json.dumps(message, default=str))
                for attr, message in zip(self.entity_data.data, payload)
            ]

        return [(self.__build_topic(), json.dumps(payload, default=str))]

    def __snapshot_publishes(self) -> List[Tuple[str, str]]:
        builder = get_snapshot_builder(
            self.connector, self.out_connector_id, self.iris_db, self.realtime_db
        )

        # With {id} in the topic, one message per item, each to its own subtopic.
        if self.__topic_uses(ID_VARIABLE):
            return [
                (self.__build_topic(item_id=item_id), json.dumps(payload, default=str))
                for item_id, payload in builder.build_payloads_by_id().items()
            ]

        payload = builder.build_payload()
        if payload is None:
            return []

        return [(self.__build_topic(), json.dumps(payload, default=str))]

    def __topic_uses(self, variable: str) -> bool:
        return any(
            part.get("type") == "variable" and part.get("value") == variable
            for part in self.connector.topicTemplate or []
        )

    def __publish(self, publishes: List[Tuple[str, str]]) -> None:
        timeout = settings.OUT_CONNECTOR_REQUEST_TIMEOUT
        client = self.__create_client()

        connected = threading.Event()
        connack = {}
        # paho calls on_publish before marking the message as published, so once
        # wait_for_publish returns its PUBACK reason is already here.
        pubacks = {}

        def on_connect(_client, _userdata, _flags, reason_code, _properties):
            connack["reason_code"] = reason_code
            connected.set()

        def on_publish(_client, _userdata, mid, reason_code, _properties):
            pubacks[mid] = reason_code

        client.on_connect = on_connect
        client.on_publish = on_publish

        try:
            client.connect(self.connector.ipAddress, self.connector.port)
            client.loop_start()

            if not connected.wait(timeout):
                raise TimeoutError(f"MQTT broker did not answer in {timeout}s")

            reason_code = connack["reason_code"]
            if reason_code.is_failure:
                raise ConnectionError(f"MQTT connection refused: {reason_code}")

            # QoS 1: the broker acknowledges each message, so one it refuses (a topic its
            # policy does not allow) is an error here instead of a silent loss.
            for topic, message in publishes:
                info = client.publish(topic, message, qos=1)
                info.wait_for_publish(timeout)
                if not info.is_published():
                    raise TimeoutError(f"MQTT message to '{topic}' not acknowledged in {timeout}s")
                reason = pubacks.get(info.mid)
                if reason is not None and reason.is_failure:
                    raise ConnectionError(f"MQTT broker refused the message to '{topic}': {reason}")
        finally:
            client.disconnect()
            client.loop_stop()

    def __create_client(self) -> mqtt.Client:
        # MQTT 5: the broker says why it refuses a connection or a message (e.g. "Not
        # authorized"); with 3.1.1 a refused publish just never gets its acknowledgement.
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self.connector.clientId or self.__generate_client_id(),
            protocol=mqtt.MQTTv5,
        )
        client.connect_timeout = settings.OUT_CONNECTOR_REQUEST_TIMEOUT

        if self.connector.username and self.connector.password:
            client.username_pw_set(self.connector.username, self.connector.password)

        if self.connector.ssl:
            # Without a CA of its own, the broker certificate is checked against the system ones.
            context = ssl.create_default_context(cadata=self.connector.sslCert or None)
            if self.connector.clientCert:
                self.__load_client_certificate(context)
            client.tls_set_context(context)
        elif self.connector.clientCert:
            raise ValueError("A client certificate needs the TLS connection")

        return client

    def __generate_client_id(self) -> str:
        """
        A different id on every connection: a broker drops a session when another arrives
        with the same id, and one connector can be sending twice at a time (a periodic and a
        manual send, or parallel notifications). The connector id keeps it traceable.
        """
        return f"{settings.OUT_CONNECTOR_CLIENT_ID_PREFIX}-c{self.out_connector_id}-{uuid.uuid4().hex[:8]}"

    def __load_client_certificate(self, context: ssl.SSLContext) -> None:
        """
        Mutual TLS: the broker authenticates the connector by its certificate.
        """
        if not self.connector.clientKey:
            raise ValueError("The client certificate has no private key")

        # ssl only loads them from files: a private folder, gone as soon as they are loaded.
        with tempfile.TemporaryDirectory(prefix="mqtt-") as folder:
            paths = []
            for name, content in (("client.crt", self.connector.clientCert), ("client.key", self.connector.clientKey)):
                path = os.path.join(folder, name)
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as handle:
                    handle.write(content)
                paths.append(path)

            context.load_cert_chain(certfile=paths[0], keyfile=paths[1])

    def __build_topic(self, measure: Optional[str] = None, item_id: Optional[str] = None) -> str:
        """
        Joins the parts of the topic template, replacing the variables with the entity data.
        The measure variable only exists in legacy, where each attribute has its own message;
        id, in the snapshots sent one message per item.
        """
        variables = {}
        if item_id is not None:
            variables[ID_VARIABLE] = topic_level(item_id)
        if self.entity_data is not None:
            variables.update(
                urn=self.entity_data.urn,
                tenant=self.entity_data.tenant,
                scope=self.entity_data.scope,
            )
        if measure is not None:
            variables["measure"] = measure

        topic = ""
        for part in self.connector.topicTemplate or []:
            value = part.get("value")
            if value is None:
                continue

            if part.get("type") == "variable":
                if value not in variables:
                    raise ValueError(f"Unknown topic variable: {value!r}")
                topic += variables[value]
            else:
                topic += value

        if not topic:
            raise ValueError("The MQTT connector has an empty topic")

        return topic


def allowed_broker_destinations() -> List[str]:
    return [
        destination.strip().lower()
        for destination in settings.MQTT_ALLOWED_DESTINATIONS.split(",")
        if destination.strip()
    ]


def check_broker_destination(host: str) -> None:
    """
    The broker host is written by whoever configures the connector, so it must be in
    the allow list (the host or a subdomain of it) and not resolve to an internal address.
    """
    allowed = allowed_broker_destinations()
    if not allowed:
        raise DestinationNotAllowed(
            "No MQTT broker is allowed (MQTT_ALLOWED_DESTINATIONS is empty): nothing is sent"
        )

    hostname = (host or "").strip().strip("[]").lower()
    if not any(hostname == entry or hostname.endswith(f".{entry}") for entry in allowed):
        raise DestinationNotAllowed(
            f"The MQTT broker '{host}' is not in the allowed destinations"
        )

    _reject_internal_host(hostname)
