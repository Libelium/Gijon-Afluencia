from enum import Enum
from functools import reduce
from typing import List

from jobs.alarms.alarm_activator.alarm_activator import AlarmActivator


class LogicSequenceOperator(str, Enum):
    """
    Funcion logica que combina las condiciones de una alarma (alarms.function).
    """

    AND = "AND"
    OR = "OR"
    XOR = "XOR"

    def get_operator(self):
        if self == LogicSequenceOperator.AND:
            return lambda a, b: a and b

        if self == LogicSequenceOperator.OR:
            return lambda a, b: a or b

        return lambda a, b: a ^ b


class LogicSequenceActivator(AlarmActivator):
    """
    Activador que agrupa otros activadores y los combina con la funcion logica
    de la alarma.
    """

    def __init__(self, operator: LogicSequenceOperator):
        self.operator = operator
        self.activators: List[AlarmActivator] = []

    def get_activators(self) -> List[AlarmActivator]:
        return self.activators

    def add_activator(self, activator: AlarmActivator) -> None:
        self.activators.append(activator)

    def activated(self) -> bool:
        if not self.activators:
            return False

        return reduce(
            self.operator.get_operator(),
            [activator.activated() for activator in self.activators],
        )

    def summary(self) -> str:
        if not self.activators:
            return "Sin condiciones evaluables"

        if len(self.activators) == 1:
            return self.activators[0].summary()

        return f" {self.operator.value} ".join(
            f"({activator.summary()})" for activator in self.activators
        )
