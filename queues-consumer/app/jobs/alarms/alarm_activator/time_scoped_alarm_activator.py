from datetime import datetime
from typing import List

from aether_pylib.time_series.time_scope import TimeScope
from jobs.alarms.alarm_activator.alarm_activator import AlarmActivator


class TimeScopedAlarmActivator(AlarmActivator):
    """
    Envuelve a otro activador y le añade el periodo de vigencia de la condicion:
    fuera del periodo, la condicion no dispara.
    """

    def __init__(
        self,
        date: datetime,
        time_scopes: List[TimeScope],
        activator: AlarmActivator,
    ):
        self.activator = activator
        self.time_scopes = time_scopes
        self.date = date

        if not self.time_scopes:
            self.catched_time_scope_result = True
            return

        self.catched_time_scope_result = any(
            time_scope.in_scope(self.date) for time_scope in self.time_scopes
        )

    def activated(self) -> bool:
        return self.catched_time_scope_result and self.activator.activated()

    def summary(self) -> str:
        if self.catched_time_scope_result:
            return self.activator.summary()

        return (
            f"{self.activator.summary()}, pero la marca de tiempo del dato recibido "
            f"({self.date}) esta fuera del periodo configurado"
        )
