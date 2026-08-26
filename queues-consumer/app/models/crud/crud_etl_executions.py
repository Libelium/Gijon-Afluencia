from models.etl_executions_model import ETLExecution
from sqlalchemy.orm import Session
from sqlalchemy import select, cast, String
from datetime import datetime, timezone
from typing import List, Optional

def get_etl_execution_with_specific_params(
    db: Session,
    etl_type: Optional[str] = None,
    user_id: Optional[int] = None,
    execution_date: Optional[str] = None,  # Can be formatted as "YYYY-MM-DD"
    params: Optional[dict] = None,
) -> List[ETLExecution]:
    """Retrieve ETL executions that match specific filters."""

    query = db.query(ETLExecution)

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
                cast(ETLExecution.params.op('->>')(key), String) == value
            )
        
    return query.all()


def create_etl_execution(
    db: Session,
    etl_type: str,
    user_id: Optional[int] = None,
    execution_date: Optional[datetime] = None,
    params: Optional[dict] = None,
) -> ETLExecution:
    """Create a new ETL execution entry."""
    params_stringified = {key: str(value) for key, value in params.items()}
    now = datetime.now()
    etl_execution = ETLExecution(
        type=etl_type,
        user_id=user_id,
        execution_date=execution_date,
        params=params_stringified,
        created_at=now,
        updated_at=now,
    )
    db.add(etl_execution)
    db.commit()
    db.refresh(etl_execution)

    return etl_execution
