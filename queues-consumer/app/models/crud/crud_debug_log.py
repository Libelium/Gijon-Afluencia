from models.debug_log_model import DebugLog
from sqlalchemy.orm import Session
from datetime import datetime
from db import deps


def create_warning_log(payload: dict) -> None:
    return
    db: Session = next(deps.get_db())
    db_debug_log = DebugLog(
        cloud_area=payload.get("cloud_area", "Py-queues-consumer"),
        name=payload.get("name"),
        tags=payload.get("tags"),
        info=payload.get("info", "Empty info"),
        created_at=datetime.now(),
    )
    db.add(db_debug_log)
    db.commit()
