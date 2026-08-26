from models.crud.crud_user import get_organization_admins
from models.crud.crud_entity import get_entities_with_permissions
from models.crud.crud_organizations import get_organization_by_id
from jobs.job import Job
from config.logging import appLogging as logging
import requests
from config.config import settings
from datetime import datetime, timedelta
from schemas.crowd_process_visitors_request_schema import (
    AllProcessVisitorsRequest,
    ProcessVisitorsRequest,
    ProcessVisitorsEntity,
)
import time
from typing import List, Optional
from sqlalchemy.orm import Session
from db.session_helpers import main_session


class ProcessVisitorsAll(Job):
    def __init__(
        self,
        request: AllProcessVisitorsRequest,
        db: Optional[Session] = None,
    ) -> None:
        self.request = request
        self._injected_main = db
        self.db: Optional[Session] = None

    def __get_crowd_users(self) -> List:
        self.all_users_with_crowd = get_organization_admins(self.db)

        logging.info(
            f"Found {len(self.all_users_with_crowd)} organization admins to process"
        )

    def __get_user_crowd_entities(self, user_id) -> None:
        """
        Retrieves the crowd entities for the user
        """
        readeable_entities = get_entities_with_permissions(
            "CrowdFlowEvent", user_id, self.db
        )

        entities = []

        for entity, scope, tenant in readeable_entities:
            entities.append(
                ProcessVisitorsEntity(
                    id=entity.id, tenant=tenant, scope=scope, urn=entity.urn
                )
            )

        return entities

    def __start_jobs(self, user_id, entities) -> None:
        """
        Enqueues one job per organization
        """
        from tasks.crowd import process_visitors_job

        current_date = datetime.now()
        
        if self.request.start_date:
            start_date = self.request.start_date
        else:
            start_date = current_date - timedelta(hours=1)

        if self.request.end_date:
            end_date = self.request.end_date
        else:
            end_date = current_date
            
        start_date = start_date.replace(minute=0, second=0, microsecond=0)
        
        end_date = end_date.replace(minute=0, second=0, microsecond=0)
        
        while start_date < end_date:
            next_date = start_date + timedelta(hours=1)

            notification = ProcessVisitorsRequest(
                user_id=user_id,
                entities=entities,
                start_date=start_date.isoformat(),
                end_date=next_date.isoformat(),
                mode="tourism",
                aggregation_mode="none",
                force=self.request.force,
            )

            logging.info(
                f"Delaying process visitors job for user {user_id} - {start_date} - {next_date}"
            )

            process_visitors_job.delay(notification)

            start_date = next_date

    def handle(self) -> None:
        """
        Handles the job execution:
        """
        logging.info(f"Starting crowd process visitors for all users")
        with main_session(self._injected_main) as db:
            self.db = db
            try:
                self.__get_crowd_users()
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
                    logging.info(f"Starting crowd process visitors for user {user.id}")
                    entities = self.__get_user_crowd_entities(user.id)

                    if len(entities) > 0:
                        self.__start_jobs(user.id, entities)
                    else:
                        logging.info(f"No entities found for user {user.id}")

            except Exception as e:
                logging.error(e)

        return None
