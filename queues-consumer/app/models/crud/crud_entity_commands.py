import datetime
from typing import Union
from models.entity_commands_model import EntityCommand
from models.entity_properties_model import EntityProperty
from sqlalchemy.orm import Session
from config.logging import appLogging as logging
from sqlalchemy.sql import func


def get_command(entity_id: int, name: str, db: Session) -> EntityCommand:
    return (
        db.query(EntityCommand)
        .filter(EntityCommand.entity_id == entity_id)
        .filter(EntityCommand.name == name)
        .first()
    )


def add_entity_command(
    urn: str,
    tenant: str,
    scope: str,
    entity_id: int,
    name: str,
    info: Union[str, dict],
    status: Union[str, dict],
    available: bool,
    pending: bool,
    pending_value: str,
    status_timestamp: datetime.datetime,
    info_timestamp: datetime.datetime,
    db: Session,
    commit: bool = True,
) -> bool:
    entity_command_params = {
        "urn": urn,
        "tenant": tenant,
        "scope": scope,
        "entity_id": entity_id,  # this is the entity_id, not the entity urn
        "name": name,
        "status": status,
        "info": info,
        "available": available,
        "pending": pending,
        "pending_value": pending_value,
        "status_timestamp": status_timestamp,
        "info_timestamp": info_timestamp,
    }

    # remove nones from the dict, so the default values are set if not provided
    entity_command_params = {
        k: v for k, v in entity_command_params.items() if v != None
    }

    entity_command_params["created_at"] = func.now()
    entity_command_params["updated_at"] = func.now()

    new_command = EntityCommand(**entity_command_params)
    db.add(new_command)
    if commit:
        db.commit()


def update_entity_command_status(
    retrieved_command: EntityCommand,
    status: Union[str, dict],
    status_timestamp: datetime.datetime,
    db: Session,
    commit: bool = True,
) -> bool:
    if status == None:
        # nothing to update
        return False

    if status_timestamp == None:
        # cannot update status without a timestamp
        logging.debug(
            f"Status timestamp not provided for EntityCommand {retrieved_command.urn}, {retrieved_command.name}. It won't be updated."
        )
        return False

    if (
        retrieved_command.status_timestamp != None
        and retrieved_command.status_timestamp >= status_timestamp
    ):
        # cannot update status if the timestamp is older than the existing one
        logging.debug(
            f"EntityCommand {retrieved_command.urn}, {retrieved_command.name} status not updated. New status timestamp is older than existing timestamp."
        )
        return False

    retrieved_command.status = status
    retrieved_command.status_timestamp = status_timestamp
    retrieved_command.updated_at = func.now()

    # because we might be also updating the info, we don't commit here unless specified
    if commit:
        db.commit()

    return True


def update_entity_command_info(
    retrieved_command: EntityCommand,
    info: Union[str, dict],
    info_timestamp: datetime.datetime,
    db: Session,
    commit: bool = True,
) -> bool:
    if info == None:
        # nothing to update
        return False

    if info_timestamp == None:
        # cannot update info without a timestamp
        logging.debug(
            f"Info timestamp not provided for EntityCommand {retrieved_command.urn}, {retrieved_command.name}. It won't be updated."
        )
        return False

    if (
        retrieved_command.info_timestamp != None
        and retrieved_command.info_timestamp >= info_timestamp
    ):
        # cannot update info if the timestamp is older than the existing one
        logging.debug(
            f"EntityCommand {retrieved_command.urn}, {retrieved_command.name} info not updated. New info timestamp is older than existing timestamp."
        )
        return False

    retrieved_command.info = info
    retrieved_command.info_timestamp = info_timestamp
    retrieved_command.updated_at = func.now()

    # because we might be also updating the status, we don't commit here unless specified
    if commit:
        db.commit()

    return True

def update_all_entity_command_status_to_pending(payload: dict, db: Session, commit: bool = True) -> bool:
    urn = payload.get("urn", None)
    tenant = payload.get("tenant", None)
    scope = payload.get("scope", None)
    entity_id = payload.get("entity_id", None)
    notified_at = payload.get("notified_at", None)

    if urn == None or tenant == None or scope == None:
        logging.warning(
            f"name, urn, tenant or scope not provided for EntityCommand status update"
        )
        return False

    if entity_id == None:
        logging.warning(
            f"entity_id not provided for EntityCommand status update"
        )
        return False

    notified_at_dt = datetime.datetime.fromtimestamp(notified_at)
    commands = (
        db.query(EntityCommand)
        .filter(
            EntityCommand.entity_id == entity_id,
            EntityCommand.pending == True,
            EntityCommand.updated_at < notified_at_dt,
        )
        .all()
    )

    if not commands:
        return False

    for command in commands:
        command.pending = False
        command.pending_value = None

    if commit:
        db.commit()

    return True



def update_entity_command(payload: dict, db: Session, commit: bool = True) -> bool:
    name = payload.get("name", None)
    urn = payload.get("urn", None)
    tenant = payload.get("tenant", None)
    scope = payload.get("scope", None)
    entity_id = payload.get("entity_id", None)

    if name == None or urn == None or tenant == None or scope == None:
        logging.warning(
            f"name, urn, tenant or scope not provided for EntityCommand update"
        )
        return False

    command = get_command(entity_id, name, db)

    # this is to be carefull with nones, because str(None) = "None"
    status = payload.get("status", None)
    status = str(status) if status != None else None
    info = payload.get("info", None)
    info = str(info) if info != None else None
    status_timestamp = payload.get("status_timestamp", None)
    info_timestamp = payload.get("info_timestamp", None)
    available = payload.get("available", None)
    pending = payload.get("pending", None)
    pending_value = payload.get("pending_value", None)

    if command:
        # now, check if we are updating status or info, and if the timestamp is newer
        # if neither status nor info are provided, we don't update anything

        update_entity_command_status(
            command, status, status_timestamp, db, commit=False
        )
        update_entity_command_info(command, info, info_timestamp, db, commit=False)

        if available != None:
            command.available = available

        if pending != None:
            command.pending = pending

        if pending_value != None:
            command.pending_value = pending_value

        if commit:
            db.commit()

    else:
        # add a new entity command
        add_entity_command(
            urn=urn,
            tenant=tenant,
            scope=scope,
            entity_id=entity_id,
            name=name,
            info=info,
            status=status,
            available=available if available != None else False,
            pending=pending if pending != None else False,
            pending_value=pending_value,
            status_timestamp=status_timestamp,
            info_timestamp=info_timestamp,
            db=db,
            commit=commit,
        )

    return True
