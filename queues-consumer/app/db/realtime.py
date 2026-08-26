from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from config.config import settings
from typing import Generator

realtime_engine = create_engine(
    settings.REALTIME_DATABASE.connection_uri,
    pool_size=1,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "connect_timeout": 10,
        "application_name": "platform-worker-realtime",
        "keepalives": 1,
        "keepalives_idle": 60,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    },
)
RealtimeSessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=realtime_engine)
)

RealtimeBase = declarative_base()


def get_db_realtime() -> Generator:
    db = RealtimeSessionLocal()
    try:
        yield db
    finally:
        db.close()
