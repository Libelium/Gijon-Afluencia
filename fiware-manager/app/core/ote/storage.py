"""
Object storage on S3 or Minio, chosen with STORAGE_TYPE.
"""

import os
from typing import Optional, Protocol

from app.core.config.logging import appLogging as log


class ObjectStorage(Protocol):
    def put(self, key: str, data: bytes) -> None: ...


class S3Storage:
    """AWS S3 via boto3. Imported lazily so the module loads without the dep."""

    def __init__(self):
        import boto3

        self.bucket = os.getenv("AWS_S3_BUCKET", "")
        self.client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_S3_ACCESS_ID") or None,
            aws_secret_access_key=os.getenv("AWS_S3_SECRET_KEY") or None,
            region_name=os.getenv("AWS_S3_REGION") or None,
        )

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)


class MinioStorage:
    """Minio, the storage the on-premise installations use (no AWS)."""

    def __init__(self):
        import io

        from minio import Minio

        self._io = io
        self.bucket = os.getenv("LOCAL_BUCKET", "")
        self.client = Minio(
            os.getenv("LOCAL_ENDPOINT", ""),
            access_key=os.getenv("LOCAL_ACCESS_ID") or None,
            secret_key=os.getenv("LOCAL_SECRET_KEY") or None,
            secure=os.getenv("LOCAL_SECURE", "false").lower() == "true",
        )
        self._bucket_checked = False

    def _ensure_bucket(self) -> None:
        """Created on first write: building the client must not make a network call."""
        if self._bucket_checked:
            return
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
        self._bucket_checked = True

    def put(self, key: str, data: bytes) -> None:
        self._ensure_bucket()
        self.client.put_object(self.bucket, key, self._io.BytesIO(data), len(data))


def get_storage() -> Optional[ObjectStorage]:
    """Resolves the storage object from STORAGE_TYPE, or None if it is not configured.

    None instead of raising: the receiver must keep answering 2xx, which the sensor
    needs to consider the frame delivered.
    """
    storage_type = os.getenv("STORAGE_TYPE", "").lower()
    try:
        if storage_type == "s3":
            return S3Storage()
        if storage_type == "local":
            return MinioStorage()
    except Exception as e:
        log.error("OTE archive: cannot build STORAGE_TYPE=%s storage: %s", storage_type, e)
        return None

    log.warning("OTE archive: STORAGE_TYPE=%r is not 's3' or 'local' — archive disabled",
                storage_type)
    return None
