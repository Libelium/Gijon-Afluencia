"""
Same contract as the reference prediction ETL (etl/base_etl.py) - init_etl/extract/
transform/load, so that a new ETL (LIDAR, or another model) hooks in the same way.
"""

import abc

class BaseETL(abc.ABC):
    @abc.abstractmethod
    def init_etl(self) -> bool:
        ...

    @abc.abstractmethod
    def extract(self) -> bool:
        ...

    @abc.abstractmethod
    def transform(self) -> bool:
        ...

    @abc.abstractmethod
    def load(self) -> bool:
        ...

    def execute_once(self) -> int:
        if self.init_etl() and self.extract() and self.transform() and self.load():
            return 0
        return -1
