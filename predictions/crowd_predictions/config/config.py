"""
Storage backend selection: s3 (AWS, DEFAULT) | local (Minio, on-premise).
"""

from functools import lru_cache

from crowd_predictions.config.settings import storage as storage_settings
from crowd_predictions.config.storage import StorageType


@lru_cache(maxsize=None)
def get_storage() -> StorageType:
    """
    Storage backend according to STORAGE_TYPE, built on the first call and reused
    afterwards (a single client per process).

    The cache holds the CLIENT, not the configuration: STORAGE_TYPE is read on
    every new construction, so a test can patch the environment and clear the
    cache with `get_storage.cache_clear()`.
    """
    storage_type = storage_settings().STORAGE_TYPE

    if storage_type == "s3":
        # Import inside the branch: boto3 is only needed if S3 is really used.
        from crowd_predictions.config.s3_storage import S3Storage
        from crowd_predictions.config.s3_storage_settings import S3StorageSettings
        conf = S3StorageSettings()
        # Checked HERE and not in the settings class, which is only built in this
        # branch: with STORAGE_TYPE=local these are legitimately empty. Passing them
        # empty to boto3 does not fail - it falls back to the node's own credential
        # chain and to Bucket(None), so it would write wherever that node can reach.
        missing = [f"AWS_S3_{f}" for f in ("ACCESS_ID", "SECRET_KEY", "BUCKET")
                   if not getattr(conf, f)]
        if missing:
            raise ValueError(f"STORAGE_TYPE=s3 but {', '.join(missing)} is not set. "
                             "Set them, or use STORAGE_TYPE=local for MinIO.")
        return S3Storage(conf)

    if storage_type == "local":
        # Same with `minio`: it is only imported in the branch that uses it.
        from crowd_predictions.config.local_storage import LocalStorage
        from crowd_predictions.config.local_storage_settings import LocalStorageSettings
        return LocalStorage(LocalStorageSettings())

    raise ValueError(f"Unknown STORAGE_TYPE: {storage_type}. Use 's3' or 'local'")
