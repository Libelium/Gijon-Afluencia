from typing import Generator
from app.core.time_series.data_sources.quantum_leap.db_settings import DBSettings
from sqlalchemy import create_engine, MetaData
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker, scoped_session


class ConnectionManager:
    """
    This class manages the connections to the
    timescale database
    """

    def __init__(self, db_settings: DBSettings):
        self.db_settings = db_settings
        # without connect_timeout libpq blocks for ~130 s and the health check
        # stays stuck on a thread
        self.engine = create_engine(
            self.db_settings.connection_uri,
            pool_size=self.db_settings.POOL_SIZE,
            max_overflow=0,
            connect_args={"connect_timeout": 3},
        )
        # the health check does not share the API pool: that one has max_overflow=0, so a
        # busy API made readiness fail on load instead of on a real outage
        self.health_engine = create_engine(
            self.db_settings.connection_uri,
            poolclass=NullPool,
            connect_args={
                "connect_timeout": 3,
                "options": "-c statement_timeout=3000",
            },
        )

        self.metadata = MetaData()
        self.session_local = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )

    def get_session(self) -> Generator:
        """
        Returns a session to the database,
        and closes it when the context is finished,
        just in case
        """
        db = self.session_local()
        try:
            yield db
        finally:
            db.close()
