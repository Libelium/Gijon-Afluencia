from dataclasses import dataclass

import dateutil.parser
from app.core.time_series.data_sources.quantum_leap.schemas.entity_schema import Entity
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    JSON,
    Double,
)

from sqlalchemy.orm import Session

from app.core.time_series.data_sources.quantum_leap.connection_manager import (
    ConnectionManager,
)
from app.core.time_series.data_sources.quantum_leap.db_settings import DBSettings
from app.core.time_series.data_sources.quantum_leap.quantum_leap_data_source import (
    QuantumLeapDataSource,
)
from app.core.time_series.data_sources.quantum_leap.models import Base
from app.core.config.logging import appLogging as logging


@dataclass
class SqliteDBSettings:
    connection_uri: str = "sqlite:///:memory:"
    POOL_SIZE: int = 10


class DeviceTableModel(Base):
    """
    A table to mock a device.
    Because sqlite does not have different schemas, we
    cannot test any functionality that depends on the schema.
    """

    __tablename__ = "etdevice"

    entity_id = Column(String, primary_key=True)
    entity_type = Column(String)
    time_index = Column(DateTime, primary_key=True)
    fiware_servicepath = Column(String)
    original_ngsi_entity = Column(JSON)
    instance_id = Column(String)
    # NGSI attributes
    name_col = Column(String)
    tmp_col = Column(Double)
    active_col = Column(Boolean)
    location_col = Column(JSON)

    # this should be located in the md_ets_metadata table, but we are mocking it here
    static_metadata = {
        "entity_id": ["id", "Text"],
        "entity_type": ["type", "Text"],
        "time_index": ["time_index", "DateTime"],
        "name_col": ["name", "Text"],
        "tmp_col": ["tmp", "Double"],
        "active_col": ["active", "Boolean"],
        "location_col": ["location", "GeoJson"],
    }


class MockDb:
    """
    A mock database for testing quantum leap data source.
    """

    def __init__(self):
        # this is all fake, just for it to work and not raise exceptions
        logging.warning("Creating mock database...")

        self.ds = QuantumLeapDataSource(
            **{
                "QL_DB_HOST": "localhost",
                "QL_DB_PORT": 5432,
                "QL_DB_USER": "user",
                "QL_DB_PASS": "password",
                "QL_DB_NAME": "quantumleap",
                "GUNICORN_WORKERS": 10,
            }
        )

        self.ds.connection_manager = ConnectionManager(SqliteDBSettings())

        # create all tables
        logging.warning("Creating tables...")
        Base.metadata.create_all(self.ds.connection_manager.get_engine())

        self.ds.table_metadata = {
            '"None"."etdevice"': DeviceTableModel.static_metadata,
        }

        self.ds.entity_tables = {}

    def get_connection_manager(self):
        return self.ds.connection_manager

    def get_ql_ds(self):
        return self.ds

    def clear_data(self):
        """
        Clear all the data in the database,
        only for the DeviceTableModel table
        """
        session = self.ds.connection_manager.get_session()
        session.query(DeviceTableModel).delete()
        session.commit()
        session.close()

        self.ds.entity_tables = {}
        self.ds.tenant_tables = {}

    def update_ds_entity_tables(self, entity: Entity) -> None:
        self.ds.entity_tables[entity] = DeviceTableModel.__table__

    def update_ds_tenant_tables(self, tenant: str, table: Table = None) -> None:
        if table is None:
            table = DeviceTableModel.__table__

        if tenant not in self.ds.tenant_tables:
            self.ds.tenant_tables[tenant] = []

        self.ds.tenant_tables[tenant].append(table)
