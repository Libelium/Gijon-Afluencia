from models.log_model import Log
from sqlalchemy.orm import Session
from datetime import datetime


def create_log(db: Session, payload: dict) -> None:
    db_log = Log(
        message=payload.get("message"),
        level_name=payload.get("level_name"),
        datetime=payload.get("datetime"),
        extra=payload.get("extra"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        resource_type=payload.get("resource_type"),
        resource_id=payload.get("resource_id"),
    )
    db.add(db_log)
    db.commit()


def create_info_log(db: Session, payload: dict) -> None:
    payload["level_name"] = "INFO"
    create_log(db, payload)


def create_error_log(db: Session, payload: dict) -> None:
    payload["level_name"] = "ERROR"
    create_log(db, payload)


def create_warning_log(db: Session, payload: dict) -> None:
    payload["level_name"] = "WARNING"
    create_log(db, payload)
