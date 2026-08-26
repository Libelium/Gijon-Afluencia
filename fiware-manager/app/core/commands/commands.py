from app.core.config.config import settings

from app.core.db.deps import get_mongo_db_connection

from app.core.config.logging import appLogging as log
from app.core.config.config import settings


def add_new_command(device_serial: str, tenant: str, scope: str, payload: dict) -> None:
    """
    Store a new command in the database, so that it can be sent to
    the device when it reports the next time
    """
    no_sql_db = get_mongo_db_connection()
    mongo_commands_collection = no_sql_db[settings.MONGO_DATABASE.DB][
        settings.PENDING_COMMANDS_COLLECTION
    ]

    # Update the document with the given serial to append the new commands to the commands array
    result = mongo_commands_collection.update_one(
        {
            "serial": device_serial,
            "tenant": tenant,
            "scope": scope,
        },
        {"$set": {f"commands.{command}": value for command, value in payload.items()}},
        upsert=True,
    )

    if result.modified_count == 0:
        log.info(
            f"Document for {device_serial} was not modified, no modifications were needed"
        )
    else:
        log.info(f"Document for {device_serial} was modified")

    if result.upserted_id is not None:
        log.info(f"Document for {device_serial} was created")

    no_sql_db.close()


def get_device_pending_commands(device_serial: str, tenant: str, scope: str) -> dict:
    """
    Returns the pending commands for a device, if any, and deletes them from the database
    (so that they are not sent again)
    """

    no_sql_db = get_mongo_db_connection()
    mongo_commands_collection = no_sql_db[settings.MONGO_DATABASE.DB][
        settings.PENDING_COMMANDS_COLLECTION
    ]

    pending_cmds_register = mongo_commands_collection.find_one_and_delete(
        {
            "serial": device_serial,
            "tenant": tenant,
            "scope": scope,
        }
    )

    log.info(
        f"Pending commands for {device_serial}, tenant: {tenant}, scope: {scope} : {pending_cmds_register}"
    )

    no_sql_db.close()

    if pending_cmds_register is None:
        return {}

    pending_cmds = pending_cmds_register.get("commands")

    return pending_cmds


def get_ik_pending_commands(i: str, k: str) -> dict:
    """
    Returns the pending commands related to the entity provisioned
    with the given i and k, if any, and deletes them from the database
    (so that they are not sent again)
    """

    no_sql_db = get_mongo_db_connection()

    iota_devices_collection = no_sql_db[settings.MONGO_DATABASE.DB]["devices"]

    device_provisioning = iota_devices_collection.find_one(
        {
            "id": i,
            "apikey": k,
        }
    )

    if device_provisioning is None:
        log.warning(f"No device provisioning found with i: {i} and k: {k}")
        return {}

    tenant = device_provisioning.get("service")
    scope = device_provisioning.get("subservice")

    return get_device_pending_commands(i, tenant, scope)
