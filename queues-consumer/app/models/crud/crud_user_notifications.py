from models.user_notification_model import UserNotification
from datetime import datetime
from sqlalchemy.orm import Session


def create_user_notification(db: Session, payload: dict) -> None:
    """
    Creates a user notification
    """

    db_user_notification = UserNotification(
        user_id=payload.get("user_id"),
        data=payload.get("data"),
        read=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(db_user_notification)
    db.commit()
