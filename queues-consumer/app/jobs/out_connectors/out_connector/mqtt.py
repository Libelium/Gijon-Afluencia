import json
import ssl
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
        payload = get_snapshot_builder(
            self.connector, self.out_connector_id, self.iris_db, self.realtime_db
        ).build_payload()

        if payload is None:
            return []

        return [(self.__build_topic(), json.dumps(payload, default=str))]

    def __publish(self, publishes: List[Tuple[str, str]]) -> None:
        timeout = settings.OUT_CONNECTOR_REQUEST_TIMEOUT
        client = self.__create_client()

        connected = threading.Event()
        connack = {}

        def on_connect(_client, _userdata, _flags, reason_code, _properties):
            connack["reason_code"] = reason_code
            connected.set()

        client.on_connect = on_connect

        try:
            client.connect(self.connector.ipAddress, self.connector.port)
            client.loop_start()

            if not connected.wait(timeout):
                raise TimeoutError(f"MQTT broker did not answer in {timeout}s")

            reason_code = connack["reason_code"]
            if reason_code.is_failure:
                raise ConnectionError(f"MQTT connection refused: {reason_code}")

            # Without waiting, disconnect() can drop the messages before they leave the socket.
            for topic, message in publishes:
                info = client.publish(topic, message)
                info.wait_for_publish(timeout)
                if not info.is_published():
                    raise TimeoutError(f"MQTT message to '{topic}' not sent in {timeout}s")
        finally:
            client.disconnect()
            client.loop_stop()

    def __create_client(self) -> mqtt.Client:
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self.connector.clientId or f"pid-{uuid.uuid4().hex[:12]}",
        )
        client.connect_timeout = settings.OUT_CONNECTOR_REQUEST_TIMEOUT

        if self.connector.username and self.connector.password:
            client.username_pw_set(self.connector.username, self.connector.password)

        if self.connector.ssl:
            # Without a CA of its own, the broker certificate is checked against the system ones.
            context = ssl.create_default_context(cadata=self.connector.sslCert or None)
            client.tls_set_context(context)

        return client

    def __build_topic(self, measure: Optional[str] = None) -> str:
        """
        Joins the parts of the topic template, replacing the variables with the entity data.
        The measure variable only exists in legacy, where each attribute has its own message.
        """
        # A snapshot carries many entities: its topic can only be static.
        variables = {}
        if self.entity_data is not None:
            variables = {
                "urn": self.entity_data.urn,
                "tenant": self.entity_data.tenant,
                "scope": self.entity_data.scope,
            }
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
