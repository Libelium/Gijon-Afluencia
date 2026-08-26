from models.virtualizations_model import Virtualizations
from typing import Optional
from typing import List
from sqlalchemy.orm import Session
from config.logging import appLogging as logging


def get_virtualizations_by_type_id(
    db: Session,
    v_type: str,
    v_id: int,
) -> List[Virtualizations]:
    """
    Returns the row(s) from `virtualizations` where the pair
    (virtualization_type, virtualization_id) matches the given arguments.
    """
    return (
        db.query(Virtualizations)
        .filter(
            Virtualizations.virtualization_type == v_type,
            Virtualizations.virtualization_id == v_id,
        )
        .all()
    )


def get_virtualizations_by_type_ids(
    db: Session,
    v_type: str,
    v_ids: List[int],
) -> List[Virtualizations]:
    """
    Returns all rows from `virtualizations` where
    (virtualization_type == v_type) AND (virtualization_id IN v_ids).
    """
    if not v_ids:
        return []

    return (
        db.query(Virtualizations)
        .filter(
            Virtualizations.virtualization_type == v_type,
            Virtualizations.virtualization_id.in_(v_ids),
        )
        .all()
    )
