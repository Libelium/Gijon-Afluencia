from abc import ABC, abstractmethod

from jobs.alarms.alarm.alarm import Alarm
from jobs.alarms.models import Alarm as AlarmModel


class AlarmBuilder(ABC):
    """
    Constructor de alarmas: recoge en varias llamadas todo lo que hace falta
    (la alarma, sus condiciones y los datos con los que evaluarlas) y al final
    devuelve la alarma montada.
    """

    @abstractmethod
    def set_alarm(self, alarm: AlarmModel) -> "AlarmBuilder":
        pass

    @abstractmethod
    def build(self) -> Alarm:
        pass
