from abc import ABC, abstractclassmethod

class Job(ABC):

    @abstractclassmethod
    def handle(self):
        pass