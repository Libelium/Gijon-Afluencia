from typing import Optional

from pydantic_settings import SettingsConfigDict

from crowd_predictions.config.settings import EnvSettings


class S3StorageSettings(EnvSettings):
    """
    AWS S3 configuration (STORAGE_TYPE=s3), from AWS_S3_* (the env_prefix).

    Read when INSTANTIATED, not when the module is imported - the old dataclass
    did the latter, which made patching os.environ in a test useless.

    Optional so the class can be built without an environment (tests). The real
    check lives in config.get_storage(), which is the only place that builds it and
    the only one that knows STORAGE_TYPE is s3 - with local (Minio) these are
    legitimately empty and this class is never instantiated.
    """

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=True,
                                     env_prefix="AWS_S3_")

    ACCESS_ID: Optional[str] = None
    SECRET_KEY: Optional[str] = None
    REGION: Optional[str] = None
    BUCKET: Optional[str] = None
