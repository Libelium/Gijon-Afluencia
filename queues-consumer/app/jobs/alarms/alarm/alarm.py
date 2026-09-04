from abc import ABC, abstractmethod


class Alarm(ABC):
    """
    Clase generica que representa una alarma ya lista para evaluarse.
    """

    @abstractmethod
    def update(self) -> None:
        """
        Actualiza el estado de la alarma y ejecuta sus acciones si hace falta.
        """
        pass
