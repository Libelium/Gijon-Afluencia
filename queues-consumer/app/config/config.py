import os
from enum import Enum

from config.cb_notification_translator import CBNotificationTranslatorSettings
from config.db_realtime_settings import DBRealtimeSettings
from config.db_settings import DBSettings
from config.general import GeneralConfig
from config.keycloak_settings import KeycloakConfig
from config.local_storage import LocalStorage
from config.local_storage_settings import (
    LocalImageStorageSettings,
    LocalStorageSettings,
)
from config.queue_worker_type import WorkerType
from config.queue_task_config import QueueTaskConfig
from config.rabbitmq import RabbitConfig
from config.s3_storage import S3Storage
from config.s3_storage_settings import S3ImageStorageSettings, S3StorageSettings
from config.sentry_settings import SentrySettings
from config.storage import StorageType
from config.timescale_settings import TimescaleDbsSettings, TimescaleSettings
from dotenv import load_dotenv
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

# Load the env file
load_dotenv()


class TimeseriesType(str, Enum):
    TIMESCALE = "timescale"
    NONE = "none"


class Settings(BaseSettings):
    TIMESCALE: TimescaleDbsSettings = TimescaleDbsSettings()
    TIMESERIES_TYPE: TimeseriesType = TimeseriesType(
        os.getenv("TIMESERIES_TYPE", "timescale")
    )
    DATABASE: DBSettings = DBSettings()
    REALTIME_DATABASE: DBRealtimeSettings = DBRealtimeSettings()
    RABBITMQ: RabbitConfig = RabbitConfig()
    SENTRY: SentrySettings = SentrySettings()
    GENERAL: GeneralConfig = GeneralConfig()
    KEYCLOAK: KeycloakConfig = KeycloakConfig()
    S3_STORAGE: S3StorageSettings = S3StorageSettings()
    S3_IMAGES_STORAGE: S3ImageStorageSettings = S3ImageStorageSettings()
    LOCAL_STORAGE: LocalStorageSettings = LocalStorageSettings()
    LOCAL_IMAGES_STORAGE: LocalImageStorageSettings = LocalImageStorageSettings()
    CB_NOTIFICATION: CBNotificationTranslatorSettings = (
        CBNotificationTranslatorSettings()
    )
    AETHER_LINK_URL: str = os.getenv("AETHER_LINK_URL", "")
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "")
    model_config = ConfigDict(case_sensitive=True)
    IOTA_URL: str = os.getenv("IOTA_URL", "")
    QUEUE_CONSUMER_WORKERS: int = int(os.getenv("QUEUE_CONSUMER_WORKERS", 1))
    WORKER_CONCURRENCY: int = int(os.getenv("WORKER_CONCURRENCY", 1))
    UVICORN_WORKERS: int = int(os.getenv("UVICORN_WORKERS", 1))

    # ---- Mobile push notifications (FCM service-account key JSON, base64; empty disables) ----
    FIREBASE_CREDENTIALS_BASE64: str = os.getenv("FIREBASE_CREDENTIALS_BASE64", "")
    # ---- Mobile push notifications, iOS (APNs .p8 key, base64; empty disables) ----
    APNS_KEY_BASE64: str = os.getenv("APNS_KEY_BASE64", "")
    APNS_KEY_ID: str = os.getenv("APNS_KEY_ID", "")
    APNS_TEAM_ID: str = os.getenv("APNS_TEAM_ID", "")
    APNS_ENVIRONMENT: str = os.getenv("APNS_ENVIRONMENT", "sandbox")
    WORKER_TYPE: WorkerType = WorkerType(os.getenv("WORKER_TYPE", "universal"))
    LAUNCH_UVICORN: bool = os.getenv("LAUNCH_UVICORN", "true") == "true"
    LAUNCH_CELERY_SCHEDULER: bool = (
        os.getenv("LAUNCH_CELERY_SCHEDULER", "true") == "true"
    )

    DAYS_OF_GRACE: int = os.getenv("DAYS_OF_GRACE", 10)
    AUTO_SYNC_INTERVAL: int = int(os.getenv("AUTO_SYNC_INTERVAL", 604800))  # weekly
    TILEMAPPER_URL: str = os.getenv("TILEMAPPER_URL", "")
    DEFAULT_EXTERNAL_REQUEST_TIMEOUT: int = int(
        os.getenv("DEFAULT_EXTERNAL_REQUEST_TIMEOUT", 5)
    )  # seconds
    OUT_CONNECTOR_REQUEST_TIMEOUT: int = int(
        os.getenv("OUT_CONNECTOR_REQUEST_TIMEOUT", 5)
    )  # seconds
    DEFAULT_AETHER_LINK_REQUEST_TIMEOUT: int = int(
        os.getenv("DEFAULT_AETHER_LINK_REQUEST_TIMEOUT", 10)
    )  # seconds
    TIMESERIES_REQUEST_TIMEOUT: int = int(
        os.getenv("TIMESERIES_REQUEST_TIMEOUT", 5 * 60)
    )  # seconds
    QUEUE_TASK_CONFIG: QueueTaskConfig = QueueTaskConfig()
    NUM_MAX_RETRIES: int = int(os.getenv("NUM_MAX_RETRIES", 5))
    CONNECTOR_DEACTIVATION_WINDOW_SECONDS: int = int(
        os.getenv("CONNECTOR_DEACTIVATION_WINDOW_SECONDS", 60)
    )  # seconds
    CROWD_PROCESS_VISITORS_INTERVAL: int = int(
        os.getenv("CROWD_PROCESS_VISITORS_INTERVAL", 60 * 60)
    )
    CROWD_FLOWS_MUNICIPALITY_INTERVAL: int = int(
        os.getenv("CROWD_FLOWS_MUNICIPALITY_INTERVAL", 60 * 60)
    )
    CROWD_CLASSIFICATION_INTERVAL: int = int(
        os.getenv("CROWD_CLASSIFICATION_INTERVAL", 60 * 60 * 24)
    )
    CROWD_UNIQUE_VISITORS_INTERVAL: int = int(
        os.getenv("CROWD_CLASSIFICATION_INTERVAL", 60 * 60 * 24)
    )
    WEB_FRONT_URL: str = os.getenv("WEB_FRONT_URL", "")
    DATA_CACHE_CROWD_PROCESS_INTERVAL: int = int(
        os.getenv("DATA_CACHE_CROWD_PROCESS_INTERVAL", 60 * 60)
    )
    DATA_CACHE_DELETE_AFTER_UPLOAD: bool = (
        os.getenv("DATA_CACHE_DELETE_AFTER_UPLOAD", "false") == "true"
    )

    IS_ON_PREMISE: bool = os.getenv("IS_ON_PREMISE", "false") == "true"
    HEALTHCHECK_INTERVAL: int = int(os.getenv("HEALTHCHECK_INTERVAL", 3000))
    HEALTHCHECK_DEVICE_DATAMODEL: str = os.getenv(
        "HEALTHCHECK_DEVICE_DATAMODEL", "DeviceHealthcheck"
    )
    HEALTHCHECK_TENANT: str = os.getenv("HEALTHCHECK_TENANT", "libelium")
    HEALTHCHECK_SCOPE: str = os.getenv("HEALTHCHECK_SCOPE", "/")
    OLD_SMSP_STORE_REALTIME_FACTOR: float = float(
        os.getenv("OLD_SMSP_STORE_REALTIME_FACTOR", 0.01)
    )
    DLQ_MAX_LENGTH: int = int(os.getenv("DLQ_MAX_LENGTH", "150000"))
    DLQ_RECOVERY_IDLE_TIMEOUT_SECONDS: int = int(
        os.getenv("DLQ_RECOVERY_IDLE_TIMEOUT_SECONDS", "30")
    )
    DLQ_RECOVERY_CHECK_INTERVAL_SECONDS: int = int(
        os.getenv("DLQ_RECOVERY_CHECK_INTERVAL_SECONDS", "10")
    )
    ENABLE_SWAGGER: bool = os.getenv("ENABLE_SWAGGER", "false") == "true"

    # ---- HTTP API access control (SEC-016, SEC-017, SEC-018, SEC-043) -------
    # Shared secret expected in the X-Queues-Consumer-Token header by /publish
    # and /stream. Deliberately has NO default: an empty value makes those
    # endpoints refuse every request (503) instead of serving them unauthenticated.
    # See app/api.py for the rationale.
    QUEUES_CONSUMER_API_TOKEN: str = os.getenv("QUEUES_CONSUMER_API_TOKEN", "")
    # Comma-separated allow list of origins for CORS. Empty means "no
    # cross-origin browser access", which is the right default for a service
    # that is ClusterIP-only and is called server-to-server.
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "")
    # Comma-separated allow list of Celery task names that /publish may dispatch.
    # Empty means "use PUBLISHABLE_TASKS_DEFAULT from app/api.py".
    PUBLISHABLE_TASKS: str = os.getenv("PUBLISHABLE_TASKS", "")
    # Root directory of the generated HLS output served by /stream. Previously
    # referenced by app/api.py but never declared here, so the endpoint raised
    # AttributeError on every request.
    STREAMING_OUTPUT_DIR: str = os.getenv("STREAMING_OUTPUT_DIR", "/code/app/tmp/streaming")
    # ---- Alarm email channel (SMTP) ----
    # The channel stays off until MAIL_HOST is filled in: an alarm with an email
    # action is still evaluated, only the notice is skipped.
    MAIL_ENABLED: bool = os.getenv("MAIL_ENABLED", "false") == "true"
    MAIL_HOST: str = os.getenv("MAIL_HOST", "")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "")
    # starttls | ssl | none
    MAIL_ENCRYPTION: str = os.getenv("MAIL_ENCRYPTION", "starttls")
    MAIL_TIMEOUT: int = int(os.getenv("MAIL_TIMEOUT", 10))

    # ---- Alarm HTTP push channel ----
    # The destination URL is written by the user, so it is an SSRF vector: only
    # the destinations listed here are called, and an empty list sends nothing.
    # Entries are either a host ("avisos.example.org", subdomains included) or a
    # URL prefix ("https://avisos.example.org/alarmas").
    HTTP_PUSH_ALLOWED_DESTINATIONS: str = os.getenv(
        "HTTP_PUSH_ALLOWED_DESTINATIONS", ""
    )
    HTTP_PUSH_REQUEST_TIMEOUT: int = int(os.getenv("HTTP_PUSH_REQUEST_TIMEOUT", 5))

    SMS_PROVIDER: str = os.getenv("SMS_PROVIDER", "aws_sns")
    SMS_API_KEY: str = os.getenv("SMS_API_KEY", "")
    SMS_API_SECRET: str = os.getenv("SMS_API_SECRET", "")
    SMS_FROM: str = os.getenv("SMS_FROM", "")
    SMS_AWS_REGION: str = os.getenv("SMS_AWS_REGION", "eu-south-2")
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", 8000))
    PROMETHEUS_MULTIPROC_DIR: str = os.getenv("PROMETHEUS_MULTIPROC_DIR", "/tmp/prometheus_multiproc")


settings = Settings()

storage: StorageType = None
images_storage: StorageType = None
if settings.STORAGE_TYPE == "s3":
    storage = S3Storage(settings.S3_STORAGE)
    images_storage = S3Storage(settings.S3_IMAGES_STORAGE)
if settings.STORAGE_TYPE == "local":
    storage = LocalStorage(settings.LOCAL_STORAGE)
    images_storage = LocalStorage(settings.LOCAL_IMAGES_STORAGE)
