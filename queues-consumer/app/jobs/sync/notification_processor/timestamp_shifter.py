from typing import List

from config.logging import appLogging as logging
from jobs.sync.notification_processor.notification_processor import (
    NotificationProcessor,
)
from schemas.entity_data_notification import EntityDataNotification
from datetime import timedelta

class TimestampShifter(NotificationProcessor):
    """
    This class shifts the timestamps of the notification by some offset (see process method).
    The purpose of this shift is to make timestamps of notifications unique in cases where the
    device sends multiple notifications in a short time span (less than 1 millisecond, which
    is Orion-LD minimum resolution in notifications).
    """

    def __init__(
        self,
        offset_percent: float = 0.25,
        datamodel_filter: List[str] = ["CrowdFlowEvent"],
    ):
        """
        offset_percent: The percentage of the timestamp to shift relative to the elapsed time between
            the measurement and the notification.
        datamodel_filter: The datamodels to apply the shift to.
        """
        self.offset_percent = offset_percent
        self.datamodel_filter = datamodel_filter

    def process(
        self, notification: EntityDataNotification
    ) -> EntityDataNotification:
        """
        Transforms the notification latest timestamps of the attributes with no timestamp override.
        The new timestamp is computed as:
            self.offset_percent * (max_timestamp - notification.notified_at) + notification.notified_at
        Which, for example, for 0.25 offset_percent, would mean that the latest timestamps are
        shifted by 25% of the elapsed time between the measurement and the notification.
        """
        if any(attr.name == 'r_cfe_block' for attr in notification.data):
            return notification

        if not notification.notified_at:
            # No notified_at timestamp, so we can't shift anything
            logging.warning("No notified_at timestamp, skipping timestamp shift")
            return notification

        if notification.type not in self.datamodel_filter:
            return notification

        max_timestamp = notification.latest_timestamp(ignore_overriden=True)

        if max_timestamp is None:
            # We are ignoring overriden timestamps, so if None:
            # 1. there is no timestamp at all, so all timestamps are the notification time
            # 2. No attributes with timestamps, so nothing to shift
            return notification

        if max_timestamp > notification.notified_at:
            # This should not happen, but if it does, we should not shift the timestamps
            logging.warning(
                f"NotifiedAt timestamp is older that the latest timestamp: {notification.notified_at} < {max_timestamp}"
                + "skipping timestamp shift"
            )
            return notification

        # Compute offset
        offset = (notification.notified_at - max_timestamp) * self.offset_percent
        transformed_timestamp = max_timestamp + offset

        logging.info(f"Shifting timestamps by {offset}")

        for attr in notification.data:
            if attr.timestamp_override or attr.timestamp != max_timestamp:
                continue

            # Shift timestamp
            attr.timestamp = transformed_timestamp

        return notification
