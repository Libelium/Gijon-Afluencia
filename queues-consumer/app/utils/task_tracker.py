from datetime import datetime, timezone
from models.crud.crud_background_tasks import (
    create_job,
    update_job,
    push_step_event,
)
from models.crud.crud_log import create_error_log
from models.background_task_event_model import BackgroundJobStep


class BackgroundJobTracker:

    def __init__(
        self,
        job_id: int,
        db,
        db_realtime,
        user_id: int = None,
    ):
        self.job_id = job_id
        self.db = db
        self.db_realtime = db_realtime
        self.user_id = user_id

    @classmethod
    def create(
        cls,
        db,
        db_realtime,
        job_type: str,
        user_id: int = None,
        name: str = None,
        total_steps: int = None,
        params: dict = None,
    ) -> "BackgroundJobTracker":
        """Create a new background job record and return a tracker for it."""
        job_id = create_job(
            db,
            db_realtime,
            job_type=job_type,
            user_id=user_id,
            name=name,
            total_steps=total_steps,
            params=params,
        )
        return cls(job_id, db, db_realtime, user_id=user_id)

    def update_params(self, params: dict) -> None:
        """Update the params field of the background job."""
        update_job(self.db, self.db_realtime, self.job_id, self.user_id, params=params)

    def start(self):
        update_job(
            self.db,
            self.db_realtime,
            self.job_id,
            self.user_id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )

    def step_start(self, order: int, name: str):
        """Push a step-running event for the step at position `order`."""
        push_step_event(self.db_realtime, self.job_id, self.user_id, name, "running", order)

    def step_complete(self, order: int, name: str):
        """Push a step-completed event for the step at position `order`."""
        push_step_event(self.db_realtime, self.job_id, self.user_id, name, "completed", order)

    def step_fail(self, order: int, name: str):
        """Push a step-failed event for the step at position `order`."""
        push_step_event(self.db_realtime, self.job_id, self.user_id, name, "failed", order)

    def complete(self):
        update_job(
            self.db,
            self.db_realtime,
            self.job_id,
            self.user_id,
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )

    def fail(self, error_message: str, extra: dict = None):
        create_error_log(self.db, {
            "message": error_message,
            "extra": extra,
            "datetime": datetime.now(),
            "resource_type": "background_jobs",
            "resource_id": self.job_id,
        })

        now = datetime.now()
        running_steps = (
            self.db_realtime.query(BackgroundJobStep)
            .filter(
                BackgroundJobStep.background_job_id == self.job_id,
                BackgroundJobStep.status == "running",
                BackgroundJobStep.order.isnot(None),
            )
            .all()
        )
        for step in running_steps:
            step.status = "failed"
            step.updated_at = now
        if running_steps:
            self.db_realtime.commit()

        update_job(
            self.db,
            self.db_realtime,
            self.job_id,
            self.user_id,
            status="failed",
            completed_at=datetime.now(timezone.utc),
        )
