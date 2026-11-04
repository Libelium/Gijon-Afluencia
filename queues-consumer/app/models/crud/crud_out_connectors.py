from datetime import datetime
from typing import Dict, List, Optional
from models.crud import crud_custom_datamodels
from models.device_model import Device
from models.entity_model import Entity
from models.out_connector_has_models_model import OutConnectorHasModels
from models.out_connector_model import OutConnector, OutConnectorStatus
from models.out_connector_mqtt_model import MqttConnector, SNAPSHOT_PAYLOAD_TYPES
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

def get_related_out_connectors(
    entity_ids: List[int], device_ids: List[int], db: Session
) -> List[OutConnector]:
    """
    Gets the active out connectors related to the given entities OR devices that send
    on every notification (snapshot connectors have their own schedule).
    """
    model_filter_conditions = []

    if entity_ids:
        model_filter_conditions.append(
            and_(
                OutConnectorHasModels.model_id.in_(entity_ids),
                OutConnectorHasModels.model_type == Entity.__tablename__,
            )
        )

    if device_ids:
        model_filter_conditions.append(
            and_(
                OutConnectorHasModels.model_id.in_(device_ids),
                OutConnectorHasModels.model_type == Device.__tablename__,
            )
        )

    # Without a filter the query would return every active connector.
    if not model_filter_conditions:
        return []

    # distinct: a connector linked to both the entity and its device is sent only once.
    return (
        db.query(OutConnector)
        .join(
            OutConnectorHasModels,
            OutConnectorHasModels.out_connector_id == OutConnector.id,
        )
        .outerjoin(
            MqttConnector,
            and_(
                OutConnector.connectable_type == MqttConnector.__tablename__,
                OutConnector.connectable_id == MqttConnector.id,
            ),
        )
        .filter(OutConnector.status == OutConnectorStatus.ACTIVE)
        .filter(or_(*model_filter_conditions))
        .filter(
            or_(
                MqttConnector.id == None,
                MqttConnector.payload_type.notin_(SNAPSHOT_PAYLOAD_TYPES),
            )
        )
        .distinct()
        .all()
    )


def get_active_snapshot_connector_ids(payload_types: List[str], db: Session) -> List[int]:
    """
    Ids of the active out connectors that send a periodic snapshot of the given types.
    """
    rows = (
        db.query(OutConnector.id)
        .join(
            MqttConnector,
            and_(
                OutConnector.connectable_type == MqttConnector.__tablename__,
                OutConnector.connectable_id == MqttConnector.id,
            ),
        )
        .filter(OutConnector.status == OutConnectorStatus.ACTIVE)
        .filter(MqttConnector.payload_type.in_(payload_types))
        .all()
    )
    return [row[0] for row in rows]


def get_linked_model_ids(out_connector_id: int, model_type: str, db: Session) -> List[int]:
    """
    Ids of the models of one type (entities, devices) linked to the out connector.
    """
    rows = (
        db.query(OutConnectorHasModels.model_id)
        .filter(OutConnectorHasModels.out_connector_id == out_connector_id)
        .filter(OutConnectorHasModels.model_type == model_type)
        .all()
    )
    return [row[0] for row in rows]


def get_units_bulk(
    db: Session,
    attributes: List[tuple[str, Optional[str]]],
) -> Dict[str, Optional[str]]:
    """
    Gets units for a list of attributes in bulk
    attributes: names (str) and an optional unit (str), [('temperature', 'celsius'), ('humidity', None)]
    """
    final_units = {}
    names_to_fetch = []

    for name, unit in attributes:
        if unit and unit != "null":
            final_units[name] = unit
        else:
            names_to_fetch.append(name)

    if names_to_fetch:
        custom_datamodels = crud_custom_datamodels.get_custom_datamodel_by_command_bulk(
            names_to_fetch, db
        )
        fetched_units_map = {cd.command: cd.units for cd in custom_datamodels}

        final_units.update(
            {name: fetched_units_map.get(name) for name in names_to_fetch}
        )

    return final_units


def get_out_connector_by_id(out_connector_id: int, iris_db: Session) -> Optional[OutConnector]:
    return (
        iris_db.query(OutConnector)
        .filter(OutConnector.id == out_connector_id)
        .first()
    )


def get_mqtt_connector(connectable_id: int, iris_db: Session) -> Optional[MqttConnector]:
    return (
        iris_db.query(MqttConnector).filter(MqttConnector.id == connectable_id).first()
    )


def update_out_connector_retries(out_connector_id: int, iris_db: Session, offset: int = 1):
    """
    Atomically increments (or decrements) the out connector retries by offset.
    """
    iris_db.query(OutConnector).filter(OutConnector.id == out_connector_id).update(
        {
            OutConnector.retries: OutConnector.retries + offset,
            OutConnector.updated_at: datetime.now(),
        },
        synchronize_session=False,
    )
    iris_db.commit()


def update_out_connector_last_connection_if_newer(
    out_connector_id: int, timestamp: datetime, iris_db: Session
) -> None:
    """
    Updates last_connection only if the given timestamp is more recent than the stored one.
    Prevents a slow worker from overwriting a more recent success.
    """
    iris_db.query(OutConnector).filter(
        OutConnector.id == out_connector_id,
        or_(
            OutConnector.last_connection == None,
            OutConnector.last_connection < timestamp,
        ),
    ).update(
        {OutConnector.last_connection: timestamp},
        synchronize_session=False,
    )
    iris_db.commit()


def update_out_connector(out_connector_id: int, new_values: dict, iris_db: Session):
    """
    Update the out connector.
    """

    out_connector = (
        iris_db.query(OutConnector).filter(OutConnector.id == out_connector_id).first()
    )

    for key, value in new_values.items():
        if hasattr(out_connector, key):
            setattr(out_connector, key, value)

    out_connector.updated_at = datetime.now()

    iris_db.commit()
    iris_db.refresh(out_connector)

    return out_connector
