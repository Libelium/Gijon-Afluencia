from models.etl_executions_model import ETLExecution
from sqlalchemy.orm import Session
from sqlalchemy import select, cast, String
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from config.config import settings

ETL_STATUS_STARTED = "started"
ETL_STATUS_SUCCESS = "success"
ETL_STATUS_FAILED = "failed"


def _apply_filters(
    query,
    etl_type: Optional[str] = None,
    user_id: Optional[int] = None,
    execution_date: Optional[str] = None,
    params: Optional[dict] = None,
):
    if etl_type:
        query = query.filter(ETLExecution.type == etl_type)

    if user_id:
        query = query.filter(ETLExecution.user_id == user_id)

    if execution_date:
        query = query.filter(ETLExecution.execution_date == execution_date)

    if params:
        params_stringified = {key: str(value) for key, value in params.items()}

        for key, value in params_stringified.items():
            query = query.filter(
                cast(ETLExecution.params.op("->>")(key), String) == value
            )

    return query


def get_etl_execution_with_specific_params(
    db: Session,
    etl_type: Optional[str] = None,
    user_id: Optional[int] = None,
    execution_date: Optional[str] = None,  # Can be formatted as "YYYY-MM-DD"
    params: Optional[dict] = None,
) -> List[ETLExecution]:
    """Retrieve ETL executions that match specific filters."""
    query = _apply_filters(
        db.query(ETLExecution), etl_type, user_id, execution_date, params
    )
    return query.all()


def find_etl_execution(
    db: Session, etl_type: str, params: dict
) -> Optional[ETLExecution]:
    """The most recent execution of `etl_type` with exactly these params, or None."""
    query = _apply_filters(db.query(ETLExecution), etl_type=etl_type, params=params)
    return query.order_by(ETLExecution.id.desc()).first()


def create_etl_execution(
    db: Session,
    etl_type: str,
    user_id: Optional[int] = None,
    execution_date: Optional[datetime] = None,
    params: Optional[dict] = None,
    status: str = ETL_STATUS_STARTED,
) -> ETLExecution:
    """Create a new ETL execution entry (status `started` until marked)."""
    params_stringified = {key: str(value) for key, value in (params or {}).items()}
    now = datetime.now()
    etl_execution = ETLExecution(
        type=etl_type,
        user_id=user_id,
        execution_date=execution_date,
        params=params_stringified,
        status=status,
        created_at=now,
        updated_at=now,
    )
    db.add(etl_execution)
    db.commit()
    db.refresh(etl_execution)

    return etl_execution


def mark_etl_execution(
    db: Session,
    execution: ETLExecution,
    status: str,
    error: Optional[str] = None,
) -> ETLExecution:
    """Record the outcome of an execution. `error` is truncated to keep the row small."""
    now = datetime.now()
    execution.status = status
    execution.error = (error or "")[:2000] or None
    execution.updated_at = now
    execution.finished_at = now if status != ETL_STATUS_STARTED else None
    db.add(execution)
    db.commit()
    db.refresh(execution)

    return execution


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def execution_is_successful(execution: Optional[ETLExecution]) -> bool:
    """
    A row with status NULL predates the status column: under the old semantics its
    existence meant "done", so it counts as a success and is not re-run.
    """
    if execution is None:
        return False
    return execution.status in (None, ETL_STATUS_SUCCESS)


def execution_is_running(
    execution: Optional[ETLExecution], now: Optional[datetime] = None
) -> bool:
    """
    `started` and recent enough to still be running. A `started` row older than
    CROWD_ETL_STALE_RUNNING_MINUTES belongs to a job the worker lost (hard kill,
    restart) and must not block a re-run.
    """
    if execution is None or execution.status != ETL_STATUS_STARTED:
        return False
    started_at = _as_utc(execution.updated_at or execution.created_at)
    if started_at is None:
        return False
    now = _as_utc(now) if now else datetime.now(timezone.utc)
    return now - started_at < timedelta(minutes=settings.CROWD_ETL_STALE_RUNNING_MINUTES)
