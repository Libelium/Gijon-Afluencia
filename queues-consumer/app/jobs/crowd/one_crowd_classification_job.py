from datetime import datetime, timedelta
from models.crud.crud_entity import get_entities_with_permissions
from schemas.crowd_classification_request_schema import (
    CrowdClassificationRequest,
    CrowdClassificationEntity,
)
from config.logging import appLogging as logging

class CrowdClassificationOneUser:
    def __init__(self, request, db):
        self.request = request
        self.db = db
        self.user_id = request.user_id

    def __get_user_crowd_entities(self):
        """
        Retrieves entities with classification permissions for the user
        """
        readable_entities = get_entities_with_permissions(
            "CrowdFlowEvent", self.user_id, self.db
        )
        return [
            CrowdClassificationEntity(
                id=entity.id, tenant=tenant, scope=scope, urn=entity.urn
            )
            for entity, scope, tenant in readable_entities
        ]

    def generate_jobs(self):
        """
        Generates job for the user using .delay()
        (same as CrowdClassificationAll but for a single user)
        """
        logging.info(f"Starting classification only for user {self.user_id}")
        entities = self.__get_user_crowd_entities()

        if not entities:
            logging.info(f"User {self.user_id} has no entities for classification")
            return

        current_date = datetime.now()
        start_date = self.request.start_date or (current_date - timedelta(days=31))
        end_date = self.request.end_date or current_date

        if start_date > end_date:
            logging.error("The start date is later than the end date")
            return

        start_date = start_date.replace(minute=0, hour=0, second=0, microsecond=0, day=1)
        end_date = end_date.replace(minute=0, hour=0, second=0, microsecond=0, day=1)

        from tasks.crowd import classification_job

        while start_date < end_date:
            next_date = (start_date + timedelta(days=31)).replace(
                minute=0, hour=0, second=0, microsecond=0, day=1
            )

            notification = CrowdClassificationRequest(
                user_id=self.user_id,
                entities=entities,
                start_date=start_date.isoformat(),
                end_date=next_date.isoformat(),
                mode="monthly",
                force=self.request.force,
            )

            logging.info(
                f"Delaying crowd classification job for user {self.user_id} - {start_date} - {next_date}"
            )

            classification_job.delay(notification)

            start_date = next_date
