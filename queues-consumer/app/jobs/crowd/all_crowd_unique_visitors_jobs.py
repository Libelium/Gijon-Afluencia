from models.crud.crud_user import get_organization_admins
from models.crud.crud_entity import get_entities_with_permissions
from models.crud.crud_organizations import get_organization_by_id
from jobs.job import Job
from config.logging import appLogging as logging
import requests
from config.config import settings
from datetime import datetime, timedelta
from schemas.crowd_unique_visitors_request_schema import (
    AllCrowdUniqueVisitorsRequest,
    CrowdUniqueVisitorsEntity,
    CrowdUniqueVisitorsRequest,
)
import time
from typing import List, Optional
from sqlalchemy.orm import Session
from db.session_helpers import main_session

class CrowdUniqueVisitorsAll(Job):
    def __init__(
        self, request: AllCrowdUniqueVisitorsRequest, db: Optional[Session] = None
    ) -> None:
        self.request = request
        self._injected_main = db
        self.db: Optional[Session] = None

    def get_crowd_users(self) -> List:
        self.all_users_with_crowd = get_organization_admins(self.db)

        logging.info(
            f"Found {len(self.all_users_with_crowd)} organization admins to process"
        )

    def get_user_crowd_entities(self, user_id) -> None:
        """
        Retrieves the crowd entities for the user
        """
        readeable_entities = get_entities_with_permissions(
            "CrowdFlowEvent", user_id, self.db
        )

        entities = []

        for entity, scope, tenant in readeable_entities:
            entities.append(
                CrowdUniqueVisitorsEntity(
                    id=entity.id, tenant=tenant, scope=scope, urn=entity.urn
                )
            )

        return entities

    def start_jobs(self, user_id, entities) -> None:
        """
        Enqueues one job per organization
        """
        from tasks.crowd import unique_visitors_job
        
        current_date = datetime.now()
        
        if self.request.start_date:
            start_date = self.request.start_date
        else:
            start_date = current_date - timedelta(days=1)

        if self.request.end_date:
            end_date = self.request.end_date
        else:
            end_date = current_date
            
        if start_date > end_date:
            logging.error("Start date is greater than end date")
            return None

        start_date = start_date.replace(minute=0, hour=0, second=0, microsecond=0)
        
        end_date = end_date.replace(minute=0, hour=0, second=0, microsecond=0)

        logging.info(f"Starting jobs for user {user_id} - {start_date} - {end_date}")

        def queue_job(agg_mode, end_time):
            """Creates and delays a unique visitors job."""
            notification = CrowdUniqueVisitorsRequest(
                user_id=user_id,
                entities=entities,
                end_date=end_time.isoformat(),
                aggregation_mode=agg_mode,
                force=self.request.force,
            )

            logging.info(
                f"Delaying crowd unique visitors job for user {user_id} "
                f"({agg_mode}) - {end_time}"
            )

            unique_visitors_job.delay(notification)
        while start_date < end_date:

            # The loop processes one day at a time
            next_date = start_date + timedelta(days=1)

            # Always trigger the Daily job
            queue_job("Daily", next_date)

            # On Monday, trigger the Weekly job
            if next_date.weekday() == 0:
                queue_job("Weekly", next_date)

            # On each Month's first day, trigger the Monthly job
            if next_date.day == 1:
                queue_job("Monthly", next_date)
                queue_job("Biweekly", next_date)

            if next_date.day == 16:
                queue_job("Biweekly", next_date)

            # Move to the next hour
            start_date = next_date


    def handle(self) -> None:
        """
        Handles the job execution:
        """
        logging.info("Starting crowd unique visitors for all users")
        with main_session(self._injected_main) as db:
            self.db = db
            try:
                self.get_crowd_users()
                users = self.all_users_with_crowd

                if self.request.organization_id:
                    org = get_organization_by_id(self.request.organization_id, self.db)
                    if org:
                        users = [u for u in users if u.id == org.admin]
                        if not users:
                            logging.warning(
                                f"Organization {self.request.organization_id} admin has no readable crowd entities"
                            )
                    else:
                        logging.warning(f"Organization {self.request.organization_id} not found")
                        return None

                for user in users:
                    logging.info(f"Starting crowd unique visitors for user {user.id}")
                    entities = self.get_user_crowd_entities(user.id)

                    if len(entities) > 0:
                        self.start_jobs(user.id, entities)
                    else:
                        logging.info(f"No entities found for user {user.id}")

            except Exception as e:
                logging.error(e)

        return None
