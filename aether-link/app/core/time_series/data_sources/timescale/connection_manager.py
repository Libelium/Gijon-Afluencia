from typing import Generator
from app.core.time_series.data_sources.quantum_leap.db_settings import DBSettings
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, scoped_session


class ConnectionManager:
    """
    This class manages the connections to the
    timescale database
    """

    def __init__(self, db_settings: DBSettings):
        self.db_settings = db_settings
        self.engine = create_engine(
            self.db_settings.connection_uri,
            pool_size=self.db_settings.POOL_SIZE,
            max_overflow=0,
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
