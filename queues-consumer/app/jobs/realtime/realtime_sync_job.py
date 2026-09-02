"""
This package is used to sync data from orion (updated_values_schema) with
the realtime database
"""

import datetime
import json
from typing import Any, List
from schemas.entity_data_notification import EntityDataNotification
from jobs.realtime.cmd_status_interpreter.cmd_status_interpreter_factory import (
    CmdStatusInterpreterFactory,
)
from schemas.resource_schema import ResourceType
from schemas.ngsi_cmd_info_schema import NgsiCmdInfo
from models.crud.crud_entity_commands import (
    update_entity_command,
    update_all_entity_command_status_to_pending,
)
from models.crud.crud_entity_properties import (
    update_entity_property,
    get_entity_property,
)
from models.crud.crud_entity_relationships import update_entity_relationship
from models.entity_properties_model import MeasureType
from config.logging import appLogging as logging
from sqlalchemy.orm import Session

_interpreter_factory = CmdStatusInterpreterFactory()


def _handle_relationship(entity_value, entity_data: EntityDataNotification, db: Session):
    """Apply a Relationship attribute update. Relationships never carry a property
    timestamp, so nothing is returned to fold into max_property_timestamp."""
    update_entity_relationship(entity_value, db, commit=False)
    return None


def _handle_property(entity_value, entity_data: EntityDataNotification, db: Session):
    """Apply a Property attribute update and return its timestamp candidate (or None
    when the value is a timestamp override, which must not move the pending cutoff)."""
    attr_name = entity_value.get("name", None)
    urn = entity_value.get("urn", None)
    tenant = entity_value.get("tenant", None)
    scope = entity_value.get("scope", None)
    if attr_name == "commands":
        command_list = entity_value.get("value", None)
        if isinstance(command_list, str):
            command_list = [command_list]
            entity_value["value"] = command_list
        process_commands_property_update(
            urn=urn,
            tenant=tenant,
            scope=scope,
            entity_id=entity_data.db_id,
            new_commands=command_list,
            db=db,
            commit=False,
        )

    update_entity_property(entity_value, db, commit=False)

    if entity_value["timestamp_override"]:
        return None
    return entity_value.get("timestamp")


def _handle_command(entity_value, entity_data: EntityDataNotification, db: Session):
    """Apply a Command attribute update. Commands never contribute a property
    timestamp, so nothing is returned to fold into max_property_timestamp."""
    process_command_update(
        entity_urn=entity_data.urn,
        entity_tenant=entity_data.tenant,
        entity_scope=entity_data.scope,
        entity_type=entity_data.type,
        entity_id=entity_data.db_id,
        cmd_name=entity_value.get("name", None),
        cmd_value=entity_value.get("value", None),
        ts=entity_value.get("timestamp", None),
        db=db,
        commit=False,
    )
    return None


# Dispatch by NGSI attribute type instead of an if/elif ladder: each handler applies
# its own attribute update and returns a timestamp candidate (Property) or None.
_ENTITY_VALUE_HANDLERS = {
    "Relationship": _handle_relationship,
    "Property": _handle_property,
    "Command": _handle_command,
}


def update_entity(
    entity_data: EntityDataNotification, realtime_db: Session, main_db: Session
):
    """
    Updates the entity values in the realtime database
    """

    logging.info(f"Updating entity values: {entity_data}")

    max_property_timestamp = None

    try:
        entity_values = _EntityNotificationData_to_EntityValues(entity_data)

        for entity_value in entity_values:
            type = entity_value.get("type", None)
            handler = _ENTITY_VALUE_HANDLERS.get(type)

            if handler is None:
                if type is None:
                    logging.info(
                        f"Type is None. Value: {entity_value}. Skipping this value."
                    )
                else:
                    logging.info(
                        f"Type is not Relationship or Property. Value: {entity_value}. Skipping this value."
                    )
                continue

            ts = handler(entity_value, entity_data, realtime_db)

            if ts is not None and (
                max_property_timestamp is None or ts > max_property_timestamp
            ):
                max_property_timestamp = ts

        # Change all commands in pending status to not pending
        if max_property_timestamp is not None:
            update_all_entity_command_status_to_pending(
                {
                    "urn": entity_data.urn,
                    "tenant": entity_data.tenant,
                    "scope": entity_data.scope,
                    "entity_id": entity_data.db_id,
                    "notified_at": max_property_timestamp.timestamp(),
                },
                realtime_db,
                commit=False,
            )

        realtime_db.commit()

    except Exception as e:
        logging.error("Error updating entity values: ", e)
        realtime_db.rollback()


def process_command_update(
    entity_urn: str,
    entity_type: str,
    entity_tenant: str,
    entity_scope: str,
    entity_id: int,
    cmd_name: str,
    cmd_value: Any,
    ts: datetime.datetime,
    db: Session,
    commit: bool = True,
):
    """
    Process the update of a command. This means updating the command status and info,
    and computing the command pending status and pending value if possible.
    """

    dict_value = json.loads(cmd_value) if isinstance(cmd_value, str) else cmd_value

    info_ts = dict_value.get("info_timestamp", ts)
    status_ts = dict_value.get("status_timestamp", ts)

    # now that we have the command value as a dict, we can get the status and info
    status = dict_value.get("status", None)
    info = dict_value.get("info", None)

    # now we can interpret the status of the command to get the pending status
    ngsi_cmd_info = NgsiCmdInfo(
        entity_urn=entity_urn,
        entity_tenant=entity_tenant,
        entity_scope=entity_scope,
        entity_type=entity_type,
        cmd_name=cmd_name,
        cmd_info=info,
        cmd_status=status,
        ts_cmd_info=info_ts,
        ts_cmd_status=status_ts,
    )

    interpreter = _interpreter_factory.build_interpreter(entity_type)

    # there might be no interpreter for this entity type,
    # in that case, we don't update the pending status (not pending by default)
    if interpreter is not None:
        is_pending, pending_value = interpreter.interpret_status(ngsi_cmd_info)
    else:
        is_pending = False
        pending_value = None

    logging.debug(
        f"Updating command {cmd_name} for entity {entity_urn} with status {status}, info {info}, is_pending {is_pending}, pending_value {pending_value}"
    )

    command_meta_info = {
        "urn": entity_urn,
        "tenant": entity_tenant,
        "scope": entity_scope,
        "entity_id": entity_id,
        "name": cmd_name,
        "status": status,
        "status_timestamp": ts,
        "info": info,
        "info_timestamp": ts,
        "pending": is_pending,
        "pending_value": pending_value,
    }
    update_entity_command(command_meta_info, db, commit=commit)


def process_commands_property_update(
    urn: str,
    tenant: str,
    scope: str,
    entity_id: int,
    new_commands: List[str],
    db: Session,
    commit: bool = True,
):
    """
    The commands are specified in the "commands" property. If this property is updated,
    we need to update the commands in the database. This could include setting some commands
    to not available, some others to available, and even adding new commands to the database.

    All is done by this function.
    """

    logging.info(
        f"Processing commands property update for entity {urn}, new commands: {new_commands}"
    )

    if new_commands is None:
        return

    old_commands_list = get_entity_property(entity_id, "commands", db)

    if old_commands_list is None:
        old_commands_list = []

    else:
        old_commands_list = json.loads(old_commands_list.value.replace("'", '"'))

    deleted_commands = [
        command for command in old_commands_list if command not in new_commands
    ]
    new_commands = [
        command for command in new_commands if command not in old_commands_list
    ]

    # set old commands to not available
    for command in deleted_commands:
        command_meta_info = {
            "name": command,
            "urn": urn,
            "tenant": tenant,
            "scope": scope,
            "entity_id": entity_id,
            "available": False,
        }
        update_entity_command(command_meta_info, db, commit=False)

    # set new commands to available
    for command in new_commands:
        command_meta_info = {
            "name": command,
            "urn": urn,
            "tenant": tenant,
            "scope": scope,
            "entity_id": entity_id,
            "available": True,
        }
        update_entity_command(command_meta_info, db, commit=False)

    if commit:
        db.commit()


def _EntityNotificationData_to_EntityValues(
    entity_data: EntityDataNotification,
) -> List[dict]:
    """
    Convert an EntityDataNotification to a list of EntityValue, which is simpler and can be reused
    for the crud of both properties and relationships.
    """

    entity_values = []

    for value in entity_data.data:
        attr_value = value.value
        attr_name = value.name
        attr_type = value.type

        if attr_name is None or attr_type is None:
            logging.info(
                f"attr_name or attr_type is None. Value: {value}. Skipping this value."
            )
            continue

        # timestamp is in seconds, convert it to datetime
        ts = datetime.datetime.fromtimestamp(value.timestamp)

        entity_values.append(
            {
                "urn": entity_data.urn,
                "tenant": entity_data.tenant,
                "scope": entity_data.scope,
                "entity_id": entity_data.db_id,
                "timestamp": ts,
                "timestamp_override": value.timestamp_override,
                "name": attr_name,
                "value": attr_value,
                "value_type": _get_attr_value_type(attr_value).value,
                "type": attr_type,
                "units": value.units,
            }
        )

    return entity_values


def _get_attr_value_type(value) -> MeasureType:
    """
    Get the type of the attribute value (the most specific type possible)
    """

    # the order of the following checks is important, be careful when changing it
    if type(value) == int or type(value) == float:
        return MeasureType.DOUBLE

    elif type(value) == bool:
        return MeasureType.BOOL

    elif isinstance(value, str):
        # try to convert the string to the most specific type possible
        try:
            value = float(value)
            return MeasureType.DOUBLE

        except ValueError:
            if value.lower() in ["true", "false"]:
                return MeasureType.BOOL

    return MeasureType.STRING
