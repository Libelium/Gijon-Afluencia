from models.failed_job_model import FailedJob
from sqlalchemy.orm import Session
from datetime import datetime
from db import deps

def create_failed_job(payload: dict, db: Session) -> None:
    return
    failed_job = FailedJob(
        connection=payload.get("connection", "Py-queues-consumer"),
        queue=payload.get("queue"),
        payload=payload.get("payload", "{}"),
        exception=payload.get("exception", "No exception info"),
        failed_at=datetime.now(),
        uuid=payload.get("uuid")
    )
    db.add(failed_job)
    db.commit()
