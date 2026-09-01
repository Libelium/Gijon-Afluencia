import os
from typing import List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

from app.core.config.db_settings import MongoDbSettings

# Load the env file
load_dotenv()


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    MONGO_DATABASE: MongoDbSettings = MongoDbSettings()
    IOTA_SOUTH_SERVICE: str = os.getenv("IOTA_SOUTH_SERVICE", "")
    # Every outbound HTTP call must be bounded: an unbounded one pins the worker
    # that made it until gunicorn gives up and aborts the whole process.
    # Plain literal, not os.getenv: BaseSettings already reads HTTP_TIMEOUT from
    # the environment by field name, and an env value would override the getenv.
    HTTP_TIMEOUT: int = 10

    # OTE (LIDAR object tracking) RAW ARCHIVE, written in gzipped batches to
    # STORAGE_TYPE + AWS_S3_*/LOCAL_* (see core/ote/storage.py).
    OTE_WEBHOOK_TOKEN: str = os.getenv("OTE_WEBHOOK_TOKEN", "")
    OTE_ARCHIVE_ENABLED: bool = os.getenv("OTE_ARCHIVE_ENABLED", "false").lower() == "true"
    OTE_ARCHIVE_PREFIX: str = os.getenv("OTE_ARCHIVE_PREFIX", "ote/incoming")
    OTE_FLUSH_SECONDS: int = int(os.getenv("OTE_FLUSH_SECONDS", "60"))
    # The memory guarantee: 4 MB x 36 sensors = 144 MB. With half-hour windows the
    # buffer reached 1.5 GB and the pod, capped at 600 MB, would have been OOM-killed.
    OTE_FLUSH_MAX_BYTES: int = int(os.getenv("OTE_FLUSH_MAX_BYTES", str(4 * 1024 * 1024)))
    OTE_MAX_BUFFER_BYTES: int = int(os.getenv("OTE_MAX_BUFFER_BYTES", str(200 * 1024 * 1024)))
    # SEC-024. Hard ceiling on the OUTPUT of gunzipping a sensor body. The buffer
    # caps above act on already-decompressed data, so they cannot stop a
    # decompression bomb: a few hundred KB of crafted gzip expands to gigabytes
    # inside `gzip.decompress` before any of them is consulted. 64 MB is ~16x the
    # largest real frame window (OTE_FLUSH_MAX_BYTES).
    OTE_MAX_DECOMPRESSED_BYTES: int = int(
        os.getenv("OTE_MAX_DECOMPRESSED_BYTES", str(64 * 1024 * 1024))
    )
    PENDING_COMMANDS_COLLECTION: str = "custom_pending_commands"
    GUNICORN_WORKERS: int = os.getenv("GUNICORN_WORKERS", 1)
    ENABLE_SWAGGER: bool = os.getenv("ENABLE_SWAGGER", False)

    TIMESTAMP_ATTRS: List[str] = (
        os.getenv("TIMESTAMP_ATTRS", "").split(",")
        if os.getenv("TIMESTAMP_ATTRS", "")
        else [
            "r_ts",
            "r_dev_ts",
            "r_dho_ts",
            "r_aqo_ts",
            "r_wto_ts",
            "r_nlo_ts",
            "r_cfo_ts",
            "r_cfe_ts",
        ]
    )

    class Config:
        case_sensitive = True


settings = Settings()
