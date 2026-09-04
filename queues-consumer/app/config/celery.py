import importlib
import os
import ssl

from celery import Celery
from config.config import settings
from config.logging import appLogging as logging
from kombu.utils.json import register_type
from pydantic import BaseModel

# Allow-list of models accepted when decoding a message: class name -> module.
# The class is resolved here, never from the module named by the message itself.
# Module paths and not classes, so each worker only imports the schemas it receives.
DESERIALIZABLE_MODELS: dict[str, str] = {
    "AllCrowdClassificationRequest": "schemas.crowd_classification_request_schema",
    "AllCrowdDataCacheETLRequest": "schemas.crowd_data_cache_etl_request_schema",
    "AllCrowdFlowsMunicipalityRequest": "schemas.crowd_flows_municipality_request_schema",
    "AllCrowdUniqueVisitorsRequest": "schemas.crowd_unique_visitors_request_schema",
    "AllProcessVisitorsRequest": "schemas.crowd_process_visitors_request_schema",
    "AutoSubscriptionRequestSchema": "schemas.auto_subscription_request_schema",
    "ContextBrokerNotification": "schemas.context_broker_notification_schema",
    "CrowdClassificationRequest": "schemas.crowd_classification_request_schema",
    "CrowdDataCacheETLRequest": "schemas.crowd_data_cache_etl_request_schema",
    "CrowdFlowsMunicipalityRequest": "schemas.crowd_flows_municipality_request_schema",
    "CrowdUniqueVisitorsRequest": "schemas.crowd_unique_visitors_request_schema",
    "DataImportationRequest": "schemas.data_importation_request",
    "EntityDataNotification": "schemas.entity_data_notification",
    "OneCrowdClassificationRequest": "schemas.crowd_classification_request_schema",
    "ProcessVisitorsRequest": "schemas.crowd_process_visitors_request_schema",
    "TypeSubscriptionMessage": "schemas.fiware_subscription_schema",
}


def serialize_pydantic(obj):
    """
    Returns a dictionary with the object's data and the model name,
    so that it can be reconstructed later
    """
    base_dict = obj.dict()
    base_dict["__model_name__"] = obj.__class__.__name__
    base_dict["__module_name__"] = obj.__class__.__module__
    return base_dict


def deserialize_pydantic(data):
    """
    Returns a pydantic model from the given data, resolving the class against
    DESERIALIZABLE_MODELS. Anything outside that list is rejected.
    """
    data.pop("__module_name__", None)
    model = data.pop("__model_name__", None)

    module_path = DESERIALIZABLE_MODELS.get(model)
    if module_path is None:
        logging.error(f"Rejected message for non-deserializable model: {model!r}")
        raise ValueError(f"Model not allowed for deserialization: {model!r}")

    model_class = getattr(importlib.import_module(module_path), model)
    return model_class(**data)


# Register the serialization and deserialization functions for pydantic models
register_type(BaseModel, "BaseModel", serialize_pydantic, deserialize_pydantic)


def ssl_options() -> dict | bool:
    """TLS for the broker, and for the result backend when it speaks amqps."""
    if settings.RABBITMQ.security != "amqps":
        return False

    # server_hostname is what makes py-amqp check the certificate name matches.
    options = {
        "cert_reqs": ssl.CERT_REQUIRED,
        "server_hostname": settings.RABBITMQ.host,
    }

    # py-amqp only loads trust anchors from ca_certs, and it must be a file: a
    # directory-only store is unusable here, so fall back to the system bundle.
    ca_file = settings.RABBITMQ.ca_file_path or ssl.get_default_verify_paths().cafile
    if not ca_file:
        raise ValueError(
            "amqps requires a CA bundle: set RABBITMQ_CA_FILE_PATH "
            "(no system trust store available)"
        )
    if not os.path.isfile(ca_file):
        raise ValueError(f"RABBITMQ CA file not found: {ca_file}")
    options["ca_certs"] = ca_file

    return options


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
