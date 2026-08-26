from app.core.time_series.data_sources.orion_ld_timescale.db_settings import DBSettings
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, scoped_session


class ConnectionManager:
    """
    This class manages the connections to the quantum leap
    timescale database
    """

    def __init__(self, db_settings: DBSettings):
        self.db_settings = db_settings
        self.engine = create_engine(
            self.db_settings.connection_uri, pool_size=self.db_settings.POOL_SIZE
        )
        self.metadata = MetaData()
        self.session_local = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=self.engine))

    def get_engine(self):
        return self.engine

    def get_metadata(self):
        return self.metadata

    def get_db_settings(self):
        return self.db_settings

    def get_session(self):
        return self.session_local()
    
    def get_bind(self):
        return self.engine.connect()
    
    def close(self):
        self.session_local.remove()
        self.engine.dispose()