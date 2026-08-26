import json
import pika
import uuid

from datetime import datetime
from schemas.entity_data_notification import EntityDataNotification
from schemas.context_broker_notification_schema import ContextBrokerNotification
from schemas.fiware_subscription_schema import TypeSubscriptionMessage


class Queue:
    def __init__(self) -> None:
        self.__create_uuid()

    def __create_uuid(self) -> None:
        self.uuid = str(uuid.uuid1())

    def set_routing_key(self, queue) -> None:
        self.__routing_key = queue

    @property
    def routing_key(self) -> str:
        return self.__routing_key

    def publish(self, client, message: dict) -> None:
        """Publish the queue with the RabbitClient, this one must be connected before"""
        client.channel.basic_publish(
            exchange="",
            routing_key=self.routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                correlation_id=message["id"],
                delivery_mode=2,
                content_type="application/json",
            ),
        )


class OrionMessagesQueue(Queue):
    def __init__(self) -> None:
        super().__init__()

    def payload(self, headers: dict, body: dict) -> dict:
        self.set_routing_key(f"fiware.orion.subscriptions")

        params = ContextBrokerNotification(headers=headers, body=body)
        return {
            "id": self.uuid,
            "task": f"fiware_orion_subscription_job",
            "params": params.dict(),
            "eta": datetime.now().timestamp(),
        }


class StoreTimeseries(Queue):
    def __init__(self) -> None:
        super().__init__()

    def payload(self, entity_data_notification: EntityDataNotification) -> dict:
        self.set_routing_key(f"data.saveTimeseries")
        return {
            "id": self.uuid,
            "task": f"save_timeseries_job",
            "params": entity_data_notification.dict(),
            "eta": datetime.now().timestamp(),
        }


class StoreRealtime(Queue):
    def __init__(self) -> None:
        super().__init__()

    def payload(self, entity_data_notification: EntityDataNotification) -> dict:
        self.set_routing_key(f"data.saveRealtime")
        return {
            "id": self.uuid,
            "task": f"save_realtime_job",
            "params": entity_data_notification.dict(),
            "eta": datetime.now().timestamp(),
        }


class TypeSubscriptionMessageQueue(Queue):
    def __init__(self) -> None:
        super().__init__()

    def payload(self, data: TypeSubscriptionMessage) -> dict:
        self.set_routing_key(f"platform.fiwareType.subscriptions")

        return {
            "id": self.uuid,
            "task": f"fiware_type_subscription_job",
            "params": data,
            "eta": datetime.now().timestamp(),
        }
