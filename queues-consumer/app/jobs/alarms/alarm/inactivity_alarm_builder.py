from datetime import datetime
from typing import Dict, List, Optional

from config.logging import appLogging as logging
from jobs.alarms.alarm.alarm import Alarm
from jobs.alarms.alarm.alarm_builder import AlarmBuilder
from jobs.alarms.alarm.inactivity_alarm import InactivityAlarm
from jobs.alarms.alarm_activator.inactivity_alarm_activator import (
    InactivityAlarmActivator,
)
from jobs.alarms.alarm_activator.logic_sequence_alarm_activator import (
    LogicSequenceActivator,
    LogicSequenceOperator,
)
from jobs.alarms.models import Alarm as AlarmModel
from jobs.alarms.models import InactivityAlarmCondition
from sqlalchemy.orm import Session


class InactivityAlarmBuilder(AlarmBuilder):
    """
    Constructor de las alarmas de inactividad.
    """

    def __init__(self):
        self.alarm: Optional[AlarmModel] = None
        self.conditions: List[InactivityAlarmCondition] = []
        self.current_timestamp: Optional[datetime] = None
        # Por cada urn, el ultimo instante de cada medida. La entrada con la
        # medida a None es el ultimo dato de la entidad, sea de la medida que sea.
        self.last_reports: Dict[str, Dict[Optional[str], datetime]] = {}
        self.id_urn_map: Dict[int, str] = {}
        self.entity_names: Dict[int, str] = {}
        self.measure_names: Dict[str, str] = {}
        self.db: Optional[Session] = None
        self.iota_service_apikey: Optional[str] = None
        self.iota_service_resource: Optional[str] = None

    def set_alarm(self, alarm: AlarmModel) -> "InactivityAlarmBuilder":
        self.alarm = alarm
        return self

    def set_current_timestamp(
        self, current_timestamp: datetime
    ) -> "InactivityAlarmBuilder":
        self.current_timestamp = current_timestamp
        return self

    def set_condition(
        self, condition: InactivityAlarmCondition
    ) -> "InactivityAlarmBuilder":
        self.conditions.append(condition)
        return self

    def set_last_reports(
        self, last_reports: Dict[str, Dict[Optional[str], datetime]]
    ) -> "InactivityAlarmBuilder":
        self.last_reports = last_reports
        return self

    def set_id_urn_map(self, id_urn_map: Dict[int, str]) -> "InactivityAlarmBuilder":
        self.id_urn_map = id_urn_map
        return self

    def set_entity_names(
        self, entity_names: Dict[int, str]
    ) -> "InactivityAlarmBuilder":
        self.entity_names = entity_names
        return self

    def set_measure_names(
        self, measure_names: Dict[str, str]
    ) -> "InactivityAlarmBuilder":
        self.measure_names = measure_names
        return self

    def set_db(self, db: Session) -> "InactivityAlarmBuilder":
        self.db = db
        return self

    def set_iota_service(
        self, apikey: Optional[str], resource: Optional[str]
    ) -> "InactivityAlarmBuilder":
        self.iota_service_apikey = apikey
        self.iota_service_resource = resource
        return self

    def build(self) -> Alarm:
        if self.alarm is None:
            raise ValueError("Falta la alarma: no se puede construir")

        if not self.conditions:
            raise ValueError(
                f"La alarma {self.alarm.id} no tiene condiciones: no se puede construir"
            )

        if self.current_timestamp is None:
            # Todas las alarmas de una pasada deben evaluarse con el mismo
            # instante; si falta, es un error del llamante, no un caso limite.
            raise ValueError("Falta el instante de evaluacion: no se puede construir")

        if self.db is None:
            raise ValueError("Falta la sesion de base de datos: no se puede construir")

        activator = LogicSequenceActivator(LogicSequenceOperator(self.alarm.function))

        for condition in self.conditions:
            urn = self.id_urn_map.get(condition.entity_id)

            if urn is None:
                logging.error(
                    f"Sin urn para la entidad {condition.entity_id} de la alarma "
                    f"{self.alarm.id}: la condicion no se evalua"
                )
                continue

            activator.add_activator(
                InactivityAlarmActivator(
                    urn=urn,
                    measure=self.measure_names.get(
                        condition.measure, condition.measure
                    ),
                    timeout_s=condition.timeout_s,
                    last_report=self.last_reports.get(urn, {}).get(condition.measure),
                    current_time=self.current_timestamp,
                    entity_name=self.entity_names.get(condition.entity_id),
                )
            )

        return InactivityAlarm(
            alarm_model=self.alarm,
            activator=activator,
            db=self.db,
            iota_service_apikey=self.iota_service_apikey,
            iota_service_resource=self.iota_service_resource,
        )
