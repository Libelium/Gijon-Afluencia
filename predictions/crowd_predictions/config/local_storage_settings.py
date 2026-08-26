from typing import Optional

from pydantic_settings import SettingsConfigDict

from crowd_predictions.config.settings import EnvSettings


class LocalStorageSettings(EnvSettings):
    """
    Minio storage configuration (STORAGE_TYPE=local), from LOCAL_* (the
    env_prefix). Same names as the ones the on-premise manifests already inject
    (STORAGE_TYPE=local, LOCAL_BUCKET, LOCAL_ENDPOINT=minio.minio.svc:9000).

    Optional because with STORAGE_TYPE=s3 none of this is configured.
    """

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=True,
                                     env_prefix="LOCAL_")

    ACCESS_ID: Optional[str] = None
    SECRET_KEY: Optional[str] = None
    # host:port, WITHOUT scheme (the Minio client does not accept "http://"). TLS
    # is decided with SECURE.
    ENDPOINT: Optional[str] = None
    BUCKET: Optional[str] = None
    SECURE: bool = False
