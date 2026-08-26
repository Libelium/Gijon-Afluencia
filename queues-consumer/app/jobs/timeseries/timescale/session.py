from typing import Generator

import jobs.timeseries.timescale.contants as constants
from config.config import settings
from config.logging import appLogging as logging
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker, Session

ts_engines = [
    create_engine(
        db.connection_uri,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "connect_timeout": 10,
            "application_name": f"platform-worker-timescale-{i}",
            "keepalives": 1,
            "keepalives_idle": 60,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
    )
    for i, db in enumerate(settings.TIMESCALE.dbs)
]

ts_session_locals = [
    scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    for engine in ts_engines
]

metadata = MetaData()

_confirmed_schemas: dict[int, set[str]] = {}


def load_known_schemas() -> None:
    """
    Pre-populate the schema cache from every configured timescale DB.
    Called once per worker process after engine dispose (worker_process_init).
    """
    for i in range(len(ts_session_locals)):
        db = next(get_session(i))
        try:
            result = db.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE :prefix"),
                {"prefix": f"{constants.SCHEMA_PREFIX}%"},
            )
            schemas = {row[0] for row in result}
            _confirmed_schemas[i] = schemas
            logging.debug(f"[schema_cache] loaded {len(schemas)} schema(s) from timescale DB {i}")
        except Exception as e:
            logging.warning(f"[schema_cache] could not preload schemas from timescale DB {i}: {e}")
        finally:
            db.close()


def get_session(db_idx: int = 0) -> Generator:
    db = ts_session_locals[db_idx]()
    try:
        yield db
    finally:
        db.close()
