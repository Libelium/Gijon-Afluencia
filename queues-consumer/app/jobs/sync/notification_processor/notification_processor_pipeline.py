from typing import List

from jobs.sync.notification_processor.timestamp_shifter import TimestampShifter
from jobs.sync.notification_processor.location_standarizer import LocationStandarizer
from jobs.sync.notification_processor.location_synchronizer import LocationSynchronizer
from jobs.sync.notification_processor.notification_processor import (
    NotificationProcessor,
)
from schemas.entity_data_notification import EntityDataNotification
from sqlalchemy.orm import Session


class NotificationProcessorPipeline(NotificationProcessor):

    def __init__(self, main_db: Session, realtime_db: Session):
        """
        Initialize the pipeline with the processors that will be applied.
        WARNING: order matters.
        """
        self.processors: List[NotificationProcessor] = [
            LocationStandarizer(),
            LocationSynchronizer(
                main_db=main_db,
                realtime_db=realtime_db,
            ),
            TimestampShifter(),
        ]

    def process(
        self, notification: EntityDataNotification
    ) -> EntityDataNotification:
        """
        Process a notification applying all the processors in the pipeline.
        """

        for processor in self.processors:
            notification = processor.process(notification)

        return notification
