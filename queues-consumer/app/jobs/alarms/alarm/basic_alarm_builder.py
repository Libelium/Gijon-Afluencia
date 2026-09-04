from datetime import datetime
from typing import Dict, List, Optional

from aether_pylib.time_series.time_scope import TimeScope
from config.logging import appLogging as logging
from jobs.alarms.alarm.alarm import Alarm
from jobs.alarms.alarm.alarm_builder import AlarmBuilder
from jobs.alarms.alarm.basic_alarm import BasicAlarm
from jobs.alarms.alarm_activator.alarm_activator import AlarmActivator
from jobs.alarms.alarm_activator.logic_sequence_alarm_activator import (
    LogicSequenceActivator,
    LogicSequenceOperator,
)
from jobs.alarms.alarm_activator.simple_operator_alarm_activator import (
    SimpleOperator,
    SimpleOperatorAlarmActivator,
)
from jobs.alarms.alarm_activator.time_scoped_alarm_activator import (
    TimeScopedAlarmActivator,
)
from jobs.alarms.models import Alarm as AlarmModel
from jobs.alarms.models import AlarmCondition
from sqlalchemy.orm import Session


class BasicAlarmBuilder(AlarmBuilder):
    """
    Constructor de las alarmas de umbral.
    """

    def __init__(self):
        self.alarm: Optional[AlarmModel] = None
        self.conditions: List[AlarmCondition] = []
        self.timestamp: Optional[datetime] = None
        self.measures: Dict[int, Dict] = {}
        self.db: Optional[Session] = None
        self.id_to_urn_map: Dict[int, str] = {}
        self.iota_service_apikey: Optional[str] = None
        self.iota_service_resource: Optional[str] = None

    def set_alarm(self, alarm: AlarmModel) -> "BasicAlarmBuilder":
        self.alarm = alarm
        return self

    def set_timestamp(self, timestamp: datetime) -> "BasicAlarmBuilder":
        """
        Marca de tiempo con la que se evalua el periodo de las condiciones.
        """
        self.timestamp = timestamp
        return self

    def set_measures(self, measures: Dict[int, Dict]) -> "BasicAlarmBuilder":
        """
        Valores con los que evaluar las condiciones, indexados por id de entidad
        y nombre de medida. Sustituye a los anteriores.
        """
        self.measures = measures
        return self

    def set_condition(self, condition: AlarmCondition) -> "BasicAlarmBuilder":
        self.conditions.append(condition)
        return self

    def set_id_to_urn_map(self, id_to_urn_map: Dict[int, str]) -> "BasicAlarmBuilder":
        self.id_to_urn_map = id_to_urn_map
        return self

    def set_db(self, db: Session) -> "BasicAlarmBuilder":
        self.db = db
        return self

    def set_iota_service(
        self, apikey: Optional[str], resource: Optional[str]
    ) -> "BasicAlarmBuilder":
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

        if self.db is None:
            raise ValueError("Falta la sesion de base de datos: no se puede construir")

        activator = LogicSequenceActivator(LogicSequenceOperator(self.alarm.function))

        for condition in self.conditions:
            condition_activator = self.__activator_from_condition(condition)

            if condition_activator is not None:
                activator.add_activator(condition_activator)

        return BasicAlarm(
            alarm_model=self.alarm,
            activator=activator,
            db=self.db,
            iota_service_apikey=self.iota_service_apikey,
            iota_service_resource=self.iota_service_resource,
        )

    def __activator_from_condition(
        self, condition: AlarmCondition
    ) -> Optional[AlarmActivator]:
        measure_value = self.measures.get(condition.entity_id, {}).get(
            condition.measure
        )

        if measure_value is None:
            logging.warning(
                f"Sin valor para la medida {condition.measure} de la entidad "
                f"{condition.entity_id}: la condicion no se evalua"
            )
            return None

        try:
            simple_operator_activator = SimpleOperatorAlarmActivator(
                reporter_name=self.id_to_urn_map.get(
                    condition.entity_id, str(condition.entity_id)
                ),
                main_operand_name=condition.measure,
                main_operand=measure_value,
                aux_operands=(condition.threshold or "").split("#"),
                operator=SimpleOperator(condition.condition),
            )

        except Exception as e:
            # Una condicion mal guardada (operador desconocido, umbrales de
            # menos) no puede tumbar la evaluacion del resto de la alarma.
            logging.error(
                f"Condicion {condition.id} de la alarma {condition.alarm_id} no "
                f"evaluable: {e}"
            )
            return None

        time_scopes = [
            TimeScope(**time_scope) for time_scope in (condition.period or [])
        ]

        return TimeScopedAlarmActivator(
            self.timestamp, time_scopes, simple_operator_activator
        )
