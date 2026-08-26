from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from models.background_task_model import BackgroundJob
from models.background_task_event_model import BackgroundJobStep
from models.log_model import Log
import models.crud.crud_resource_permissions as crud_resource_permissions

def create_job(
    db: Session,
    db_realtime: Session,
    job_type: str,
    user_id: int = None,
    name: str = None,
    total_steps: int = None,
    params: dict = None,
) -> int:
    """
    Creates a new background job with status 'queued', persists it to the main DB,
    pushes a job-level event to the realtime DB, and returns the new job's id.
    """
    now = datetime.now()
    job = BackgroundJob(
        type=job_type,
        status="queued",
        user_id=user_id,
        name=name,
        total_steps=total_steps,
        params=params,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if user_id is not None:
        crud_resource_permissions.assign_default_permissions_to_user(user_id, job, db)

    _push_step_event(db_realtime, job.id, user_id, name=None, status="queued", order=None)

    return job.id


def update_job(
    db: Session,
    db_realtime: Session,
    job_id: int,
    user_id: int = None,
    **kwargs,
) -> None:
    """
    Updates the specified fields on a background job, commits, and pushes a
    job-level realtime event (order=None). Pass any BackgroundJob field as a kwarg.
    """
    job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
    for key, value in kwargs.items():
        setattr(job, key, value)
    job.updated_at = datetime.now(timezone.utc)
    db.commit()

    _push_step_event(
        db_realtime,
        job_id,
        user_id,
        name=None,
        status=kwargs.get("status", job.status),
        order=None,
    )


def push_step_event(
    db_realtime: Session,
    job_id: int,
    user_id: Optional[int],
    name: str,
    status: str,
    order: int,
) -> None:
    """
    Pushes a step-level event (order=N) to the realtime DB.
    """
    _push_step_event(db_realtime, job_id, user_id, name, status, order)

def _push_step_event(
    db_realtime: Session,
    job_id: int,
    user_id: Optional[int],
    name: Optional[str],
    status: str,
    order: Optional[int],
) -> None:
    """
    Upserts a row in background_jobs_steps keyed by (background_job_id, order).
    - First call for a given order → INSERT.
    - Subsequent calls → UPDATE status + updated_at on the existing row.
    order=None → job-level status row; order=N → step N row.
    """
    query = db_realtime.query(BackgroundJobStep).filter(
        BackgroundJobStep.background_job_id == job_id
    )
    if order is None:
        query = query.filter(BackgroundJobStep.order.is_(None))
    else:
        query = query.filter(BackgroundJobStep.order == order)

    existing = query.first()

    now = datetime.now()
    if existing:
        existing.status = status
        existing.updated_at = now
    else:
        db_realtime.add(BackgroundJobStep(
            background_job_id=job_id,
            user_id=user_id,
            name=name,
            status=status,
            order=order,
            created_at=now,
            updated_at=now,
        ))

    db_realtime.commit()
