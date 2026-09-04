from jobs.alarms.alarm.basic_alarm import BasicAlarm


class InactivityAlarm(BasicAlarm):
    """
    La alarma de inactividad se comporta igual que la de umbral: lo unico que
    cambia es como se construye (InactivityAlarmBuilder) y, con ello, sus
    activadores.
    """

    pass
