from typing import List, Tuple
from models.action_email_model import ActionEmail
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from models.custom_datamodels_model import CustomDatamodel


def get_custom_datamodels(db: Session) -> List[CustomDatamodel]:
    """
    Retrieves all custom datamodels from the database.
    """
    return db.query(CustomDatamodel).all()


def get_custom_datamodel_by_command(command: str, db: Session) -> CustomDatamodel:
    """
    Retrieves a custom datamodel by its command.
    """
    return db.query(CustomDatamodel).filter(CustomDatamodel.command == command).first()


def get_custom_datamodel_by_command_bulk(
    commands: List[str], db: Session
) -> List[CustomDatamodel]:
    """
    Retrieves custom datamodels by a list of commands.
    """
    return db.query(CustomDatamodel).filter(CustomDatamodel.command.in_(commands)).all()
