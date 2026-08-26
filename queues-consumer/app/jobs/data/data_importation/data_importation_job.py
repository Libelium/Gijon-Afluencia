import os
from typing import List, Optional
import datetime

from config.config import storage
from config.logging import appLogging as logging
from db.session_helpers import main_session, realtime_session
from jobs.data.data_importation.factory.parser_factory import ParserFactory
from jobs.job import Job
from models.crud.crud_entity import get_or_create_entity, get_related_devices
from utils.task_tracker import BackgroundJobTracker
import models.crud.crud_user_notifications as crud_user_notifications
from schemas.data_importation_request import DataImportationRequest
from schemas.entity_data_notification import EntityDataNotification
import helpers.aether_link.aether_link_helper as aether_link_helper

from sqlalchemy.orm import Session


class DataImportationJob(Job):
    """
    Job responsible for processing data importation from a stored file.

    It orchestrates the complete importation flow, which includes:
    1. File download.
    2. Content parsing to generate data notifications.
    3. Processing and persistence of notifications in the databases.
    4. Temporary file cleanup.
    5. Logging of the final status and user notification.
    """
    def __init__(
        self,
        request: DataImportationRequest,
        main_db: Optional[Session] = None,
        realtime_db: Optional[Session] = None,
    ):
        self.request = request
        self._injected_main = main_db
        self._injected_realtime = realtime_db
        self.main_db: Optional[Session] = None
        self.realtime_db: Optional[Session] = None
        self.parser = ParserFactory().get_parser(
            # type or file extension
            request.storage_file_path.split(".")[-1]
        )

    def handle(self):
        """
        Main handler for data importation job.
        Downloads file from storage, parses it, and processes all notifications.
        """
        filename = os.path.basename(self.request.storage_file_path)
        file_format = self.request.storage_file_path.split(".")[-1].upper()

        with main_session(self._injected_main) as main_db, \
                realtime_session(self._injected_realtime) as realtime_db:
            self.main_db = main_db
            self.realtime_db = realtime_db

            tracker = BackgroundJobTracker.create(
                self.main_db,
                self.realtime_db,
                job_type="data.importation",
                user_id=self.request.user_id,
                name=f"Import [{file_format}] - {filename}",
                total_steps=4,
                params={"file": filename, "format": file_format},
            )
            tracker.start()

            try:
                # Step 1 - Download file
                tracker.step_start(1, "Downloading file")
                local_file_path = self._download_file_from_storage()
                tracker.step_complete(1, "Downloading file")

                # Step 2 - Parse file
                tracker.step_start(2, "Parsing file")
                notifications = self._parse_file(local_file_path)
                tracker.update_params({"file": filename, "format": file_format, "entities": len(notifications)})
                tracker.step_complete(2, "Parsing file")

                # Step 3 - Process data + cleanup
                tracker.step_start(3, "Processing data")
                self._process_notifications(notifications)
                self._cleanup(local_file_path)
                tracker.step_complete(3, "Processing data")

                # Step 4 - Notify user
                tracker.step_start(4, "Saving & notifying")
                self._send_notification(
                    title="Data importation completed",
                    extra_data={"notifications_count": len(notifications)},
                )
                tracker.step_complete(4, "Saving & notifying")

                logging.info(f"Data importation completed successfully for {filename}")
                tracker.complete()

            except Exception as e:
                logging.error(
                    f"Failed to process data importation for {filename}: {e}",
                    exc_info=True,
                )
                self._send_notification(
                    title="Data importation failed",
                    extra_data={"error": str(e)},
                )
                tracker.fail(str(e))
                raise

    def _download_file_from_storage(self) -> str:
        """
        Download file from configured storage to a temporary local file.

        Returns:
            Path to the downloaded temporary file
        """
        try:
            filename = os.path.basename(self.request.storage_file_path)

            local_path = storage.download_file(filename, self.request.storage_file_path)

            logging.info(f"Downloaded file {filename} from storage")

            return local_path

        except Exception as e:
            logging.error(
                f"Failed to download file {os.path.basename(self.request.storage_file_path)} from storage: {e}",
                exc_info=True,
            )
            raise

    def _parse_file(self, file_path: str) -> List[EntityDataNotification]:
        """
        Parse the downloaded file using the appropriate parser.

        Args:
            file_path: Path to the local file to parse

        Returns:
            List of EntityDataNotification objects
        """
        try:
            notifications = self.parser.parse(file_path, self.request)

            logging.info(
                f"Parsed {len(notifications)} notification(s) from {file_path}"
            )

            return notifications

        except Exception as e:
            logging.error(
                f"Failed to parse file {file_path}: {e}",
                exc_info=True,
            )
            raise

    def _process_notifications(
        self, notifications: List[EntityDataNotification]
    ) -> None:
        """
        Process each notification: get/create entity, create in Context Broker if new, store in s3
        and save to databases.

        Args:
            notifications: List of notifications to process
        """
        from tasks.sync import save_realtime_job, save_timeseries_job

        for notification in notifications:

            if not notification.data:
                logging.warning(
                    f"Skipping notification with no data for URN {notification.urn}"
                )
                continue

            try:
                entity, created = get_or_create_entity(
                    payload={
                        "urn": notification.urn,
                        "datamodel": notification.type,
                        "tenant": notification.tenant,
                        "scope": notification.scope,
                    },
                    db=self.main_db,
                    creation_check=True, 
                )

                if not entity:
                    logging.error(
                        f"Could not find or create entity for URN {notification.urn}. Skipping."
                    )
                    continue

                if created:
                    try:
                        # Build attributes from all notification data
                        attributes = {
                            attr.name: {"type": attr.type.value, "value": attr.value}
                            for attr in notification.data
                        }

                        # Ensure name attribute exists, fallback to URN last segment
                        if "name" not in attributes or not attributes["name"].get("value"):
                            attributes["name"] = {
                                "type": "Property",
                                "value": notification.urn.split(":")[-1],
                            }

                        success = aether_link_helper.create_context_broker_entity(
                            tenant=notification.tenant,
                            scope=notification.scope,
                            entities=[
                                {
                                    "id": notification.urn,
                                    "type": notification.type,
                                    "attributes": attributes,
                                }
                            ]
                        )
                        
                        if success:
                            logging.info(
                                f"Successfully created entity {notification.urn} in Context Broker"
                            )
                        else:
                            logging.warning(
                                f"Failed to create entity {notification.urn} in Context Broker"
                            )
                            
                    except Exception as e:
                        logging.error(
                            f"Error creating entity {notification.urn} in Context Broker: {e}",
                            exc_info=True
                        )

                if entity.datamodel != notification.type:
                    logging.warning(
                        f"Entity '{notification.urn}' has datamodel '{entity.datamodel}' "
                        f"but notification is for type '{notification.type}'. Proceeding anyway."
                    )

                # Enrich notification with entity data
                notification.db_id = entity.id
                notification.devices = get_related_devices(entity.id, self.main_db)

                # Save to timeseries database
                save_timeseries_job(notification)

                # Save all data to realtime database
                self._save_all_to_realtime(notification)

                logging.info(
                    f"Successfully processed notification for {notification.urn}"
                )

            except Exception as e:
                logging.error(
                    f"Failed to process notification for {notification.urn}: {e}",
                    exc_info=True,
                )

    def _save_all_to_realtime(
        self, notification: EntityDataNotification
    ) -> None:
        """
        Save all data points to the realtime database.
        """
        from tasks.sync import save_realtime_job

        if not notification.data:
            return

        try:
            save_realtime_job(notification)
        except Exception as e:
            logging.error(
                f"Failed to save all realtime data for {notification.urn}: {e}",
                exc_info=True,
            )
            raise
    def _cleanup(self, file_path: str) -> None:
        """
        Remove the temporary downloaded file and the s3 file

        Args:
            file_path: Path to the file to remove
        """
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logging.debug(f"Cleaned up temporary file {file_path}")

            storage.delete_file(self.request.storage_file_path)

        except Exception as e:
            logging.warning(f"Failed to clean up temporary file {file_path}: {e}")

    def _send_notification(self, title: str, extra_data: dict) -> None:
        """
        Send a push notification to the user about the importation status.

        Args:
            title: Notification title
            extra_data: Additional data to include in the notification
        """
        notification_data = {
            "Title": title,
            "filename": os.path.basename(self.request.storage_file_path),
            **extra_data,
        }

        crud_user_notifications.create_user_notification(
            self.realtime_db,
            {
                "user_id": self.request.user_id,
                "title": title,
                "data": notification_data,
            },
        )
