from abc import ABC, abstractmethod


class AlarmActivator(ABC):
    """
    Clase generica que representa el activador de una alarma. Una alarma esta
    disparada si su activador devuelve True.
    """

    @abstractmethod
    def activated(self) -> bool:
        """
        Comprueba si la alarma esta disparada.
        """
        pass

    @abstractmethod
    def summary(self) -> str:
        """
        Resumen del activador, para el registro de la alarma.
        """
        pass
