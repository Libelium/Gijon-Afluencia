from abc import ABC, abstractmethod


class OutConnector(ABC):
    """
    Generic class that represents an out_connector
    """

    @abstractmethod
    def handle(self) -> bool:
        """
        Sends the data through the connector. Returns False when there was nothing
        to send; raises on failure.
        """
        pass
