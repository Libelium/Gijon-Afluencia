from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from models.status_update_model import StatusUpdate


def create_status_update(payload: dict, db_realtime: Session) -> None:
    """
    Creates a new status update.
    """

    status_update = StatusUpdate(
        user_id=payload["user_id"],
        source=payload["source"],
        status=payload["status"],
        created_at=func.now(),
        updated_at=func.now(),
    )

    db_realtime.add(status_update)
    db_realtime.commit()
    db_realtime.refresh(status_update)
    return status_update
