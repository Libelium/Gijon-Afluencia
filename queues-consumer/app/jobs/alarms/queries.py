"""
Consultas de las tablas de alarmas y de sus acciones.
"""

from typing import Dict, List, Set, Tuple

from jobs.alarms.models import (
    Action,
    ActionEmail,
    ActionEntityCommand,
    ActionHttpPush,
    ActionSms,
    ActionTelegram,
    ActionWhatsapp,
    Alarm,
    AlarmCondition,
    AlarmHasAction,
    AlarmTrigger,
    AlarmType,
    InactivityAlarmCondition,
)
from models.entity_model import Entity
from models.entity_properties_model import EntityProperty
from sqlalchemy import and_, or_, tuple_
from sqlalchemy.orm import Session
from sqlalchemy.sql import func


def update_alarm_status(alarm_id: int, new_status: bool, db: Session) -> None:
    """
    Actualiza el estado de la alarma con el id dado.
    """
    alarm = db.query(Alarm).filter(Alarm.id == alarm_id).first()

    if not alarm:
        return

    alarm.up = new_status
    db.commit()


def get_related_basic_alarms(
    entity_urn: str, measure_ids: List[str], db: Session
) -> List[Tuple[Alarm, AlarmCondition]]:
    """
    Devuelve las alarmas de umbral afectadas por la entidad y las medidas dadas,
    con TODAS sus condiciones: para evaluar la funcion logica de la alarma hacen
    falta tambien las condiciones que esta actualizacion no toca.
    """
    alarm_ids = [
        row.id
        for row in db.query(Alarm.id)
        .join(AlarmCondition, AlarmCondition.alarm_id == Alarm.id)
        .join(Entity, Entity.id == AlarmCondition.entity_id)
        .filter(Entity.urn == entity_urn)
        .filter(AlarmCondition.measure.in_(measure_ids))
        .filter(Alarm.disabled == False)  # noqa: E712 - filtro SQL, no comparacion Python
        .filter(Alarm.type == AlarmType.BASIC.value)
        .all()
    ]

    if not alarm_ids:
        return []

    return (
        db.query(Alarm, AlarmCondition)
        .join(AlarmCondition, AlarmCondition.alarm_id == Alarm.id)
        .filter(Alarm.id.in_(alarm_ids))
        .all()
    )


def get_inactivity_alarms(
    db: Session,
) -> List[Tuple[str, Alarm, InactivityAlarmCondition]]:
    """
    Devuelve todas las alarmas de inactividad activas con sus condiciones, como
    tuplas (urn de la entidad, alarma, condicion).
    """
    return (
        db.query(Entity.urn, Alarm, InactivityAlarmCondition)
        .join(InactivityAlarmCondition, InactivityAlarmCondition.alarm_id == Alarm.id)
        .join(Entity, Entity.id == InactivityAlarmCondition.entity_id)
        .filter(Alarm.disabled == False)  # noqa: E712
        .filter(Alarm.type == AlarmType.INACTIVITY.value)
        .all()
    )


def get_last_reports(
    entity_measures: Dict[str, Set[str]], realtime_db: Session
) -> List[Tuple[str, str, object]]:
    """
    Ultimo instante en que cada (urn, medida) reporto, leyendo la tabla de tiempo
    real. Devuelve tuplas (urn, medida, timestamp).

    El GROUPING SETS calcula de una vez el maximo por (urn, medida) y el maximo
    por urn: la fila con medida nula es la que atiende a las condiciones de
    inactividad que no fijan medida ("cualquier dato de la entidad").
    """
    if not entity_measures:
        return []

    last_reports_per_measure = (
        realtime_db.query(
            EntityProperty.urn,
            EntityProperty.name,
            func.max(EntityProperty.timestamp),
        )
        .filter(EntityProperty.urn.in_(list(entity_measures.keys())))
        .group_by(
            func.grouping_sets(
                tuple_(EntityProperty.urn, EntityProperty.name),
                EntityProperty.urn,
            )
        )
        .subquery()
    )

    entity_conditions = []

    for entity_urn, measures in entity_measures.items():
        named_measures = [measure for measure in measures if measure is not None]
        measure_conditions = []

        if named_measures:
            measure_conditions.append(
                last_reports_per_measure.c.name.in_(named_measures)
            )

        if None in measures:
            measure_conditions.append(last_reports_per_measure.c.name.is_(None))

        if not measure_conditions:
            continue

        entity_conditions.append(
            and_(
                last_reports_per_measure.c.urn == entity_urn,
                or_(*measure_conditions),
            )
        )

    if not entity_conditions:
        return []

    return (
        realtime_db.query(last_reports_per_measure)
        .filter(or_(*entity_conditions))
        .all()
    )


def get_alarm_action_ids(
    alarm_id: int, trigger: AlarmTrigger, db: Session
) -> List[int]:
    """
    Ids de las acciones ligadas a la alarma para la transicion dada.
    """
    return [
        row.action_id
        for row in db.query(AlarmHasAction.action_id)
        .filter(AlarmHasAction.alarm_id == alarm_id)
        .filter(AlarmHasAction.type == trigger.value)
        .all()
    ]


"""
Tabla de detalle de cada canal soportado, indexada por el actionable_type que
escribe el backend (Relation::morphMap en AppServiceProvider).
"""
ACTION_MODELS = {
    "action_telegram": ActionTelegram,
    "action_sms": ActionSms,
    "action_whatsapp": ActionWhatsapp,
    "action_email": ActionEmail,
    "action_http_push": ActionHttpPush,
    "action_entity_command": ActionEntityCommand,
}


def get_actions_of_type(
    action_ids: List[int], actionable_type: str, db: Session
) -> List[Tuple[Action, object]]:
    """
    Acciones del canal dado que estan entre los ids indicados. Las de cualquier
    otro canal se ignoran.
    """
    model = ACTION_MODELS.get(actionable_type)

    if model is None or not action_ids:
        return []

    return (
        db.query(Action, model)
        .join(model, Action.actionable_id == model.id)
        .filter(Action.id.in_(action_ids))
        .filter(Action.actionable_type == actionable_type)
        .all()
    )
