"""
What a storage backend has to do, so the 17 places calling get_storage() do not care
whether they got S3 (AWS) or MinIO (on-premise).

Every method is abstract: a backend missing one then fails when it is BUILT, not halfway
through a run. list_prefix/list_subprefixes used to be optional and the LIDAR compaction
depends on both.
"""

import abc


class StorageType(abc.ABC):
    @abc.abstractmethod
    def upload_file(self, filename: str, path: str) -> str:
        """Uploads the local file `path` to the storage under the key `filename`."""

    @abc.abstractmethod
    def download_file(self, filename: str, path: str) -> str:
        """Downloads the key `filename` from the storage to the local path `path`."""

    @abc.abstractmethod
    def delete_file(self, path: str):
        """Removes the key. MUST NOT raise if it is not there: the LIDAR compaction
        deletes objects that may never have been uploaded."""

    def delete_files(self, keys: list) -> None:
        """Removes many keys. Overridden by the backends that can do it in ONE call: the
        LIDAR compaction deletes one dump per minute and sensor, and one round trip each
        was half the time of a run. The default loop keeps any other backend working."""
        for key in keys:
            self.delete_file(key)

    @abc.abstractmethod
    def list_prefix(self, prefix: str) -> list:
        """Every key under `prefix`, recursively and COMPLETE, paginating if the backend
        pages: a truncated listing leaves dumps unprocessed with nothing failing."""

    @abc.abstractmethod
    def list_subprefixes(self, prefix: str) -> list:
        """The immediate "directories" under `prefix`, to discover the device ids without
        walking the whole tree."""
