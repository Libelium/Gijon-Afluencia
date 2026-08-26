"""
Same pattern as the reference prediction ETL (config/s3_storage.py) - boto3 directly,
with no layer of our own on top. Only used if STORAGE_TYPE=s3 (see config.py).
"""

import boto3

from crowd_predictions.config.s3_storage_settings import S3StorageSettings
from crowd_predictions.config.storage import StorageType


class S3Storage(StorageType):
    def __init__(self, conf: S3StorageSettings):
        self.resource = boto3.resource(
            "s3",
            aws_access_key_id=conf.ACCESS_ID,
            aws_secret_access_key=conf.SECRET_KEY,
            region_name=conf.REGION,
        )
        self.bucket = self.resource.Bucket(conf.BUCKET)

    def upload_file(self, filename: str, path: str) -> str:
        self.bucket.upload_file(path, filename)
        return path

    def download_file(self, filename: str, path: str) -> str:
        # Through the CLIENT and not the bucket resource: boto3 documents clients as
        # thread-safe and resources as not, and the LIDAR compaction downloads a whole
        # hour of dumps from a thread pool over this single instance.
        self.bucket.meta.client.download_file(self.bucket.name, filename, path)
        return path

    def delete_file(self, path: str):
        self.bucket.Object(path).delete()
        return True

    def delete_files(self, keys: list) -> None:
        """One DeleteObjects call per 1000 keys instead of one DELETE each."""
        for start in range(0, len(keys), 1000):
            batch = keys[start:start + 1000]
            answer = self.bucket.delete_objects(
                Delete={"Objects": [{"Key": key} for key in batch], "Quiet": True})
            for failure in answer.get("Errors", []):
                # Raised, not logged: the caller deletes dumps it has just archived, and
                # one surviving would be compacted again into a second object.
                raise RuntimeError(f"Could not delete {failure.get('Key')}: {failure}")

    def list_prefix(self, prefix: str) -> list:
        return [obj.key for obj in self.bucket.objects.filter(Prefix=prefix)]

    def list_subprefixes(self, prefix: str) -> list:
        """Via the paginator and Delimiter, not by listing the whole subtree: the raw
        tree is one file every few minutes per sensor, so a recursive listing to
        find the device ids would page through millions of keys."""
        paginator = self.bucket.meta.client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.bucket.name, Prefix=prefix, Delimiter="/")
        return [common["Prefix"] for page in pages
                for common in page.get("CommonPrefixes", [])]
