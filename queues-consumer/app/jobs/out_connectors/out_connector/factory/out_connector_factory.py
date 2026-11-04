from typing import Optional

import models.crud.crud_out_connectors as crud_out_connectors
from jobs.out_connectors.out_connector.mqtt import MqttConnector
from jobs.out_connectors.out_connector.out_connector import OutConnector
from models.out_connector_model import OutConnector as OutConnectorModel
from schemas.entity_data_notification import EntityDataNotification
from sqlalchemy.orm import Session


class OutConnectorFactory:
    """
    This helper class is responsible for building the out_connector that sends
    the data of an entity, according to the connector type.
    """

    def __init__(self):
        # Keys are the morph aliases the backend stores in connectable_type.
        self.__build_map = {
            "mqtt_connector": self.__build_mqtt_connector,
        }

    def __build_mqtt_connector(
        self,
        out_connector: OutConnectorModel,
        entity_data: Optional[EntityDataNotification],
        iris_db: Session,
        realtime_db: Optional[Session],
    ) -> OutConnector:
        mqtt_connector = crud_out_connectors.get_mqtt_connector(
            out_connector.connectable_id, iris_db
        )
        if mqtt_connector is None:
            raise ValueError(
                f"MQTT connector {out_connector.connectable_id} not found for out connector {out_connector.id}"
            )

        return MqttConnector(
            out_connector.id,
            mqtt_connector,
            entity_data,
            iris_db,
            bool(out_connector.use_readable_names),
            realtime_db,
        )

    def build_out_connector(
        self,
        out_connector: OutConnectorModel,
        entity_data: Optional[EntityDataNotification],
        iris_db: Session,
        realtime_db: Optional[Session] = None,
    ) -> OutConnector:
        """
        entity_data is the notification to send, or None for a periodic snapshot.
        """
        builder = self.__build_map.get(out_connector.connectable_type)
        if builder is None:
            raise ValueError(
                f"Unsupported out connector type: {out_connector.connectable_type!r}"
            )

        return builder(out_connector, entity_data, iris_db, realtime_db)
