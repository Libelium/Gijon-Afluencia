from schemas.payload_schema import LegacyPayload, NormalizedPayload, KeyValuePayload
from models.out_connector_mqtt_model import MqttConnector as MqttConnectorModel
from sqlalchemy.orm import Session

from ..payload.base_payload import BasePayloadBuilder
from ..payload.legacy import LegacyPayloadBuilder
from ..payload.normalized import NormalizedPayloadBuilder
from ..payload.key_value import KeyValuePayloadBuilder
from ..payload.snapshot_base import SnapshotPayloadBuilder
from ..payload.occupancy_readings import OccupancyReadingsPayloadBuilder
from ..payload.flow_readings import FlowReadingsPayloadBuilder
from ..payload.device_inventory import DeviceInventoryPayloadBuilder

SNAPSHOT_BUILDERS = {
    "occupancy_readings": OccupancyReadingsPayloadBuilder,
    "flow_readings": FlowReadingsPayloadBuilder,
    "device_inventory": DeviceInventoryPayloadBuilder,
}


def get_snapshot_builder(
    connector: MqttConnectorModel,
    out_connector_id: int,
    iris_db: Session,
    realtime_db: Session,
) -> SnapshotPayloadBuilder:
    builder = SNAPSHOT_BUILDERS.get(connector.payload_type)
    if builder is None:
        raise ValueError(f"Unsupported snapshot payload type: {connector.payload_type!r}")

    return builder(out_connector_id, iris_db, realtime_db)


class PayloadFactory:
    """
    This helper class is responsible for building the payload builder according to the payload format.
    """

    def __init__(self):
        self.__build_map = {
            "legacy": self.__build_legacy_payload,
            "normalized": self.__build_normalized_payload,
            "key_value": self.__build_key_value_payload,
            "key-value": self.__build_key_value_payload,
        }

    def __build_legacy_payload(
        self,
        connector: MqttConnectorModel,
        iris_db: Session,
        use_readable_names: bool = False,
    ) -> list[LegacyPayload]:
        """
        Build a legacy payload instance.
        """
        return LegacyPayloadBuilder(connector, iris_db, use_readable_names)

    def __build_normalized_payload(
        self,
        connector: MqttConnectorModel,
        iris_db: Session,
        use_readable_names: bool = False,
    ) -> NormalizedPayload:
        """
        Build a normalized payload instance.
        """
        return NormalizedPayloadBuilder(iris_db, use_readable_names)

    def __build_key_value_payload(
        self,
        connector: MqttConnectorModel,
        iris_db: Session,
        use_readable_names: bool = False,
    ) -> KeyValuePayload:
        """
        Build a key value payload instance.
        """
        return KeyValuePayloadBuilder(iris_db, use_readable_names)

    def get_payload_builder(
        self,
        connector: MqttConnectorModel,
        iris_db: Session,
        use_readable_names: bool = False,
    ) -> BasePayloadBuilder:
        """
        Build the payload builder according to the payload format.
        """

        builder = self.__build_map.get(connector.payload_type)
        if builder is None:
            raise ValueError(f"Unsupported payload type: {connector.payload_type!r}")

        return builder(connector, iris_db, use_readable_names)
