from datetime import datetime, timezone
from typing import Optional

from jobs.alarms.alarm_activator.alarm_activator import AlarmActivator


class InactivityAlarmActivator(AlarmActivator):
    """
    Activador de las condiciones de inactividad: dispara cuando el ultimo dato
    de la entidad (o de una de sus medidas) es mas antiguo que el tiempo de
    espera configurado.
    """

    def __init__(
        self,
        urn: str,
        measure: Optional[str],
        timeout_s: int,
        last_report: Optional[datetime],
        current_time: datetime,
        entity_name: Optional[str] = None,
    ):
        self.urn = urn
        self.measure = measure
        self.timeout_s = timeout_s
        self.last_report = last_report
        self.current_time = current_time
        self.entity_name = entity_name

    def activated(self) -> bool:
        """
        Sin ningun dato previo no se dispara: la alarma vigila que los datos
        dejen de llegar, no que nunca hayan llegado.
        """
        if self.last_report is None:
            return False

        # La tabla de tiempo real guarda timestamps con zona y el reloj del job
        # es ingenuo: sin igualar las dos formas, la resta revienta.
        last_report = self.last_report
        current_time = self.current_time

        if (last_report.tzinfo is None) != (current_time.tzinfo is None):
            last_report = self.__as_utc(last_report)
            current_time = self.__as_utc(current_time)

        return (current_time - last_report).total_seconds() > self.timeout_s

    def summary(self) -> str:
        entity_info = self.entity_name if self.entity_name else self.urn
        measure_info = f" y la medida {self.measure}" if self.measure else ""

        return (
            f"Alarma de inactividad de {entity_info}{measure_info} con un tiempo de "
            f"espera de {self.timeout_s} segundos"
        )

    @staticmethod
    def __as_utc(date: datetime) -> datetime:
        if date.tzinfo is None:
            return date.replace(tzinfo=timezone.utc)

        return date.astimezone(timezone.utc)
