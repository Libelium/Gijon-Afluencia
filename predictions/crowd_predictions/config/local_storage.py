"""
Minio storage (STORAGE_TYPE=local), the one used by the the platform on-premise
deployments that have no AWS.

"""

import logging
import os

from minio import Minio

from crowd_predictions.config.local_storage_settings import LocalStorageSettings
from crowd_predictions.config.storage import StorageType

logger = logging.getLogger(__name__)

# The client returns a stream, not the whole file in memory: the model can be
# large.
_STREAM_CHUNK_BYTES = 32 * 1024


class LocalStorage(StorageType):
    def __init__(self, conf: LocalStorageSettings):
        self.client = Minio(
            conf.ENDPOINT,
            access_key=conf.ACCESS_ID,
            secret_key=conf.SECRET_KEY,
            secure=conf.SECURE,
        )
        self.bucket = conf.BUCKET
        # The bucket is checked/created lazily, on the first upload, and NOT here:
        # building the backend must not make a network call (same criterion as
        # S3Storage, and get_storage() is also used in paths that only download).
        self._bucket_checked = False

    def _ensure_bucket(self):
        """Creates the bucket if it does not exist. Idempotent and cached per process."""
        if self._bucket_checked:
            return
        if not self.client.bucket_exists(self.bucket):
            logger.info(f"Bucket '{self.bucket}' does not exist: creating it")
            self.client.make_bucket(self.bucket)
        self._bucket_checked = True

    def upload_file(self, filename: str, path: str) -> str:
        """Uploads the local file `path` to the storage under the key `filename`."""
        self._ensure_bucket()
        self.client.fput_object(self.bucket, filename, path)
        return path

    def download_file(self, filename: str, path: str) -> str:
        """
        Downloads the key `filename` from the storage to the local path `path`.

        `path` is the REAL destination: the callers (etl/predict/extract.py) read
        from the path they passed in, not from the returned value.
        """
        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        response = self.client.get_object(self.bucket, filename)
        try:
            with open(path, "wb") as file_data:
                for chunk in response.stream(_STREAM_CHUNK_BYTES):
                    file_data.write(chunk)
        finally:
            # get_object returns a urllib3 response with the connection open;
            # without this the pool runs out after a few downloads.
            response.close()
            response.release_conn()

        return path

    def delete_file(self, path: str):
        self.client.remove_object(self.bucket, path)
        return True

    def delete_files(self, keys: list) -> None:
        """remove_objects is lazy: its result MUST be consumed or nothing is deleted."""
        from minio.deleteobjects import DeleteObject
        errors = list(self.client.remove_objects(
            self.bucket, [DeleteObject(key) for key in keys]))
        if errors:
            # Raised, not logged: a dump that survives is compacted again into a second
            # object, duplicating its frames in the archive for good.
            raise RuntimeError(f"Could not delete {len(errors)} object(s): {errors[:3]}")

    def list_prefix(self, prefix: str) -> list:
        return [obj.object_name
                for obj in self.client.list_objects(self.bucket, prefix=prefix, recursive=True)]

    def list_subprefixes(self, prefix: str) -> list:
        """recursive=False makes minio return the common prefixes as is_dir entries -
        the cheap way to discover the device ids without walking the whole raw tree."""
        return [obj.object_name
                for obj in self.client.list_objects(self.bucket, prefix=prefix, recursive=False)
                if obj.is_dir]
