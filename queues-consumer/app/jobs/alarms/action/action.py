from abc import ABC, abstractmethod


class Action(ABC):
    """
    Clase generica que representa la accion de una alarma.
    """

    @abstractmethod
    def run(self) -> None:
        """
        Ejecuta la accion.
        """
        pass
