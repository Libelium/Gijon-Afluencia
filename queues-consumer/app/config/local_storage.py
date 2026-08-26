import os
from config.local_storage_settings import LocalStorageSettings
import time
from config.storage import StorageType
from minio import Minio
from config.logging import appLogging as logging


class LocalStorage(StorageType):
    def __init__(self, conf: LocalStorageSettings):
        self.client = Minio(
            conf.ENDPOINT,
            access_key=conf.ACCESS_ID,
            secret_key=conf.SECRET_KEY,
            secure=conf.SECURE,
        )

        self.bucket = conf.BUCKET
        self.files_path = conf.FILES_PATH

    def download_file(self, filename: str, path: str) -> str:
        """Download a file from S3 to the local filesystem
        :param filename: The name of the file to downloaded from S3
        :param path: The path of the file in local
        :return: The path of the downloaded file
        """
        local_path = f"/code/app/{self.files_path}/{filename}"

        # create folder temp_files if not exists
        try:
            os.mkdir(f"/code/app/{self.files_path}")
        except FileExistsError:
            pass

        content = self.client.get_object(self.bucket, path)

        with open(local_path, "wb") as file_data:
            for d in content.stream(32 * 1024):
                file_data.write(d)

        return local_path

    def list_all(self):
        for bucket_file in self.client.list_objects(self.bucket):
            print(bucket_file)

    def upload_file(self, filename: str, path: str) -> str:
        """Upload a file from the local filesystem to S3
        :param filename: The name of the file in S3
        :param path: The path of the file in local
        :return: The path of the uploaded file
        """
        self.client.fput_object(self.bucket, filename, path)
        return path

    def delete_file(self, path: str):
        self.client.Object(self.bucket, path).remove()
        return True

    def delete_folder(self, path: str):
        raise NotImplementedError("Not implemented")
