import ssl
import sys

from celery import Celery
from config.config import settings
from config.logging import appLogging as logging
from kombu.utils.json import register_type
from pydantic import BaseModel

"""
Configure celery app so that pydantic models can be serialized and deserialized
"""


def serialize_pydantic(obj):
    """
    Returns a dictionary with the object's data and the module and model name,
    so that it can be reconstructed later
    """
    base_dict = obj.dict()
    base_dict["__module_name__"] = obj.__module__
    base_dict["__model_name__"] = obj.__class__.__name__
    return base_dict


def deserialize_pydantic(data):
    """
    Returns a pydantic model from the given data,
    it must contain the module and model name as
    in the serialize_pydantic function
    """
    module = data.pop("__module_name__")
    model = data.pop("__model_name__")
    model_class = getattr(sys.modules[module], model)
    return model_class(**data)


# Register the serialization and deserialization functions for pydantic models
register_type(BaseModel, "BaseModel", serialize_pydantic, deserialize_pydantic)


def ssl_options() -> dict | bool:
    if settings.RABBITMQ.security == "amqps":
        return {
            "cert_reqs": ssl.CERT_NONE,
        }
    else:
        return False


logging.info("Creating celery app")
logging.info(f"Worker type: {settings.WORKER_TYPE}")
configured_queues = settings.WORKER_TYPE.get_queues()
queue_names = [queue.name for queue in configured_queues]
logging.info(f"Configured queues: {queue_names}")

# Create the celery app. It should be used across the whole application
app = Celery(
    "tasks",
    broker=settings.RABBITMQ.connection_slug,
    task_queues=configured_queues,
    broker_connection_retry_on_startup=True,
    broker_use_ssl=ssl_options(),
    timezone="UTC",
    disable_rate_limits=True,
    broker_pool_limit=0,
    ignore_result=True,
    broker_transport_options={
        "confirm_publish": True,
        'delivery_acknowledgement_timeout': 7200000, # 2 hours in milliseconds
        'confirm_timeout': 7200000 # Good practice to keep this consistent if used},
    }
)

app.conf.beat_dburi = settings.DATABASE.connection_uri
app.conf.beat_scheduler = "sqlalchemy_celery_beat.schedulers:DatabaseScheduler"

# Default arguments for all tasks
DEFAULT_TASK_ARGS = {
    "bind": True,
    "serializer": "json",
    "ignore_result": True,
}  # Load the tasks from the tasks module

from celery.signals import task_postrun, worker_init, worker_process_init


@worker_process_init.connect
def init_worker_process(**kwargs):
    """
    Called once per child process immediately after fork.
    Disposes engines inherited from the parent so each child
    creates its own fresh connections (fork safety).
    """
    from db.session import engine, SessionLocal
    from db.realtime import realtime_engine, RealtimeSessionLocal
    from jobs.timeseries.timescale.session import ts_engines, ts_session_locals

    engine.dispose()
    SessionLocal.remove()

    realtime_engine.dispose()
    RealtimeSessionLocal.remove()

    for ts_engine in ts_engines:
        ts_engine.dispose()
    for ts_sl in ts_session_locals:
        ts_sl.remove()

    logging.debug("[worker_process_init] all engines disposed after fork")

    if "tasks.sync" in settings.WORKER_TYPE.get_task_modules():
        from jobs.timeseries.timescale.session import load_known_schemas
        load_known_schemas()


@worker_init.connect
def preload_heavy_dependencies(**kwargs):
    # Pre-import heavy dependencies in the main worker process before it forks
    # concurrency children (prefork pool). Fork is copy-on-write: .so pages
    # loaded here are physically shared across all child workers.
    import importlib

    for mod in settings.WORKER_TYPE.get_preload_modules():
        try:
            importlib.import_module(mod)
            logging.debug(f"[preload] {mod}")
        except ImportError:
            logging.debug(f"[preload] skipped {mod} (not installed)")

    logging.info(f"[preload] done for worker type '{settings.WORKER_TYPE}'")


@task_postrun.connect
def close_db_sessions(*args, **kwargs):
    from db.session import SessionLocal
    from db.realtime import RealtimeSessionLocal
    from jobs.timeseries.timescale.session import ts_session_locals

    try:
        SessionLocal.remove()
        logging.debug("[close_db_sessions] main_db session closed")
    except Exception as e:
        logging.error(f"[close_db_sessions] Error closing main_db session: {e}")

    try:
        RealtimeSessionLocal.remove()
        logging.debug("[close_db_sessions] realtime_db session closed")
    except Exception as e:
        logging.error(f"[close_db_sessions] Error closing realtime_db session: {e}")

    for ts_session_local in ts_session_locals:
        try:
            ts_session_local.remove()
        except Exception as e:
            logging.error(f"[close_db_sessions] Error closing timescale session: {e}")
    logging.info("[close_db_sessions] timescale sessions closed")


import tasks

import metrics
metrics.setup()
