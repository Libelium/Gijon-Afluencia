from typing import List, Optional

import random

from jobs.sync.mapping_schemas.factory.mapping_schema_factory import (
    MappingSchemaFactory,
)
import jobs.sync.check_errors_sync as check_errors
import jobs.sync.smsp_verticals_sync as smsp_verticals_sync
from config.config import settings
from config.logging import appLogging as logging
from db.session_helpers import main_session, realtime_session
from jobs.job import Job
from jobs.sync.notification_processor.notification_processor_pipeline import (
    NotificationProcessorPipeline,
)
from models.crud.crud_entity import (
    get_devices_with_expired_subscription,
    get_or_create_entity,
    get_related_devices,
)

from schemas.context_broker_notification_schema import ContextBrokerNotification
from schemas.entity_data_notification import EntityDataNotification
from sqlalchemy.orm import Session
from tasks.sync import save_realtime_job, save_timeseries_job
from metrics.collectors.sync_metrics import SyncMetricsCollector


class EntitySync(Job):
    """
    This class is responsible for handling the EntitySync job.
    This job is the one that receives the raw notification from the
    context broker. For now, it expects the notification to be
    in NGSI-LD normalized format.
    """

    def __init__(
        self,
        payload: ContextBrokerNotification,
        db: Optional[Session] = None,
        realtime_db: Optional[Session] = None,
    ):
        self.payload: ContextBrokerNotification = payload
        self.mapping_schema_factory = MappingSchemaFactory()
        self._injected_main = db
        self._injected_realtime = realtime_db
        # Sessions and the dependent processor_pipeline are bound in handle()
        # so we don't capture connections at module import time.
        self.db: Optional[Session] = None
        self.realtime_db: Optional[Session] = None
        self.processor_pipeline: Optional[NotificationProcessorPipeline] = None

    def get_observers_for_notification(
        self, notification: EntityDataNotification
    ) -> List:
        """
        This method returns the list of observers to be notified for a given notification.
        So far, only CrowdFlowEvent has specific observers.
        The rest of the notifications will use the default observers.
        """

        base_observers = [
            self.check_errors,
            self.check_smsp_veticals,
        ]

        optional_job_observers = [
            self.enqueue_save_realtime,
            self.enqueue_alarms_job,
        ]

        default_observers = base_observers + optional_job_observers

        # TIP: update this to filter new datamodels
        observer_map = {"CrowdFlowEvent": (base_observers + [self.save_cfe_commands])}

        return observer_map.get(notification.type, default_observers)

    def handle(self) -> None:
        logging.info(f"Handling EntitySync job: {self.payload}")

        with main_session(self._injected_main) as db, \
                realtime_session(self._injected_realtime) as realtime_db:
            self.db = db
            self.realtime_db = realtime_db
            self.processor_pipeline = NotificationProcessorPipeline(db, realtime_db)

            try:
                if self._is_deletion_notification():
                    logging.info("Skipping deletion notification")
                    return

                translator = settings.CB_NOTIFICATION.get_translator()
                notification_data = translator.translate(self.payload)

                for entity_data in notification_data.data:
                    self._process_single_entity(entity_data)

            except Exception as e:
                logging.error(f"CRITICAL ERROR during job handling: {e}. Re-queueing.")
                raise e

    def _is_deletion_notification(self) -> bool:
        """
        Context Broker sends a root-level "deletedAt" on each entity when it is deleted.
        Discard those notifications so downstream processing does not recreate the entity.
        """
        entities = self.payload.body.get("data", []) or []
        return any(isinstance(e, dict) and "deletedAt" in e for e in entities)

    def _process_single_entity(self, entity_data: EntityDataNotification) -> None:
        """
        Orchestrates the processing lifecycle for a single entity by calling
        dedicated methods for refresh, transformation, and dispatching.
        """

        SyncMetricsCollector.record_entity(
            tenant=entity_data.tenant,
            attribute_count=len(entity_data.data),
            payload_bytes=len(entity_data.model_dump_json().encode()),
        )

        refresh_entity_data = self._refresh_and_validate_entity(entity_data)
        if not refresh_entity_data:
            return

        notifications_to_dispatch = self._transform_notification(refresh_entity_data)
        if not notifications_to_dispatch:
            return

        self._dispatch_jobs(notifications_to_dispatch)

    def _refresh_and_validate_entity(
        self, entity_data: EntityDataNotification
    ) -> EntityDataNotification | None:
        """
        Retrieves entity from DB, enriches the notification object with DB data,
        and validates its subscription.
        Returns the enriched object or None if validation fails.
        """
        entity, was_created = get_or_create_entity(
            payload={
                "urn": entity_data.urn,
                "datamodel": entity_data.type,
                "tenant": entity_data.tenant,
                "scope": entity_data.scope,
            },
            db=self.db,
            creation_check=True,
        )

        if entity is None:
            logging.error(
                f"Ignoring entity {entity_data.urn} ({entity_data.type}): not found or could not be created."
            )
            return None

        entity_data.db_id = entity.id
        entity_data.recently_created = was_created
        entity_data.devices = get_related_devices(entity.id, self.db)

        if self.__is_expired(entity.id):
            logging.warning(f"Ignoring entity {entity.id} due to expired subscription.")
            return None

        return entity_data

    def _transform_notification(
        self, entity_data: EntityDataNotification
    ) -> List[EntityDataNotification]:
        """
        Applies processing pipelines and mapping schemas to the notification.
        Returns a list of final notifications to be dispatched (original + virtual).
        """
        try:
            processed_entity_data = self.processor_pipeline.process(entity_data)
        except Exception as e:
            logging.error(f"Error in processing pipeline for {entity_data.urn}: {e}")
            return []

        try:
            mapping_schemas = self.mapping_schema_factory.get_mapping_schemas(
                self.db, processed_entity_data
            )
            virt_notifications = []
            for mapping_schema in mapping_schemas:
                virt_notifications.extend(mapping_schema.apply(processed_entity_data))
        except Exception as e:
            logging.error(f"Error applying mapping schemas for {entity_data.urn}: {e}")
            virt_notifications = []

        return virt_notifications + [processed_entity_data]

    def _dispatch_jobs(self, notifications: List[EntityDataNotification]) -> None:
        """
        Dispatches all non-critical and critical jobs for a list of notifications.
        The critical job (save_timeseries) will re-raise an exception on failure
        to trigger a message re-queue.
        """
        for notification in notifications:
            # Dispatch CRITICAL job: Save Timeseries
            try:
                logging.debug(f"Attempting to save timeseries for {notification.urn}")
                save_timeseries_job(notification)
                logging.info(
                    f"Timeseries job enqueued successfully for {notification.urn}"
                )
            except Exception as e:
                logging.error(
                    f"CRITICAL: Failed to enqueue timeseries job for {notification.urn}. Re-queueing message. Error: {e}"
                )
                raise e

            # Dispatch non-critical jobs (Observers)
            for job_publisher in self.get_observers_for_notification(notification):
                try:
                    job_publisher(notification)
                except Exception as e:
                    logging.error(
                        f"Error dispatching non-critical job '{job_publisher.__name__}' for {notification.urn}: {e}"
                    )

    def check_errors(
        self, entity_data_notification: EntityDataNotification
    ) -> None:
        if entity_data_notification:
            check_errors.sync_errors(
                entity_data_notification, self.db, self.realtime_db
            )

    def enqueue_save_realtime(
        self, entity_data_notification: EntityDataNotification
    ) -> None:
        """
        Enqueues a job to save the realtime data of the entity.
        """

        save_realtime_job.delay(entity_data_notification)

    def enqueue_alarms_job(
        self, entity_data_notification: EntityDataNotification
    ) -> None:
        """
        Enqueues a job to evaluate the threshold alarms of the entity.
        """

        # Deferred import: tasks.alarms pulls in the alarm engine, which imports
        # jobs. Breaks the cycle and keeps an engine failure inside this observer.
        from tasks.alarms import alarms_job

        alarms_job.delay(entity_data_notification)

    def __is_expired(self, entity_id: int) -> bool:
        """
        Handles the data of an entity, ensuring only devices with valid subscriptions are updated.
        """
        expired_devices = get_devices_with_expired_subscription(
            entity_id, self.db, settings.DAYS_OF_GRACE
        )
        if expired_devices:
            logging.warning(
                f"Devices with expired subscriptions for entity {entity_id}: {expired_devices}"
            )

        return len(expired_devices) > 0

    def check_smsp_veticals(
        self, entity_data_notification: EntityDataNotification
    ) -> None:
        """
        This method is responsible for updating the related entities according
        to the SMSp verticals reporting.
        """
        smsp_verticals_sync.sync_verticals(entity_data_notification, self.db)

    def save_cfe_commands(self, entity_data_notification: EntityDataNotification):
        """
        This method is responsible for syncing the CFE commands for Smart Spot devices.
        """
        max_timestamp = entity_data_notification.latest_timestamp()

        for attr in entity_data_notification.data:
            if (
                (attr.name == "name" and attr.timestamp == max_timestamp)
                or ("w_" in attr.name and attr.timestamp == max_timestamp)
                or (attr.name == "r_cfe_block")
            ):

                logging.info(f"Syncing CFE commands for {entity_data_notification.urn}")
                self.enqueue_save_realtime(entity_data_notification)
                return

        if random.random() < settings.OLD_SMSP_STORE_REALTIME_FACTOR:
            logging.info(
                f"Enqueuing realtime save for old Smart Spots 1%: {entity_data_notification.urn}"
            )
            self.enqueue_save_realtime(entity_data_notification)

