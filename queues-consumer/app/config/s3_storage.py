from config.s3_storage_settings import S3StorageSettings
import time
import boto3
from boto3 import s3
from config.storage import StorageType

import os


class S3Storage(StorageType):
    def __init__(self, conf: S3StorageSettings):
        self.resource = boto3.resource(
            "s3",
            aws_access_key_id=conf.ACCESS_ID,
            aws_secret_access_key=conf.SECRET_KEY,
            region_name=conf.REGION,
        )
        self.client = boto3.client(
            "s3",
            aws_access_key_id=conf.ACCESS_ID,
            aws_secret_access_key=conf.SECRET_KEY,
            region_name=conf.REGION,
        )

        self.bucket = self.resource.Bucket(conf.BUCKET)
        self.files_path = conf.FILES_PATH

    def download_file(self, filename: str, path: str) -> str:
        """Download a file from S3 to the local filesystem
        :param filename: The name of the file to download
        :param path: The path of the file in S3
        :return: The path of the downloaded file
        """
        local_path = f"/code/app/{self.files_path}/{filename}"

        # create folder temp_files if not exists
        try:
            os.mkdir(f"/code/app/{self.files_path}")
        except FileExistsError:
            pass

        self.bucket.download_file(path, local_path)
        return local_path

    def list_all(self):
        for bucket_file in self.bucket.objects.all():
            print(bucket_file)

    def upload_file(self, filename: str, path: str) -> str:
        """Upload a file from the local filesystem to S3
        :param filename: The name of the file to upload
        :param path: The path of the file in S3
        :return: The path of the uploaded file
        """
        self.bucket.upload_file(path, filename)
        return path

    def delete_file(self, path: str):
        self.bucket.Object(path).delete()
        return True

    def delete_folder(self, path: str):
        for obj in self.bucket.objects.filter(Prefix=path):
            obj.delete()
        return True
