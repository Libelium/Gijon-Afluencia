from abc import ABC, abstractmethod


class StorageType(ABC):
    @abstractmethod
    def download_file(self, filename: str, path: str) -> str:
        """
        Download a file from storage to the local filesystem
        :param filename: The name of the file to download
        :param path: The path of the file in the storage
        :return: The path of the downloaded file
        """
        pass

    @abstractmethod
    def upload_file(self, filename: str, path: str) -> str:
        """
        Upload a file from the local filesystem to the storage
        :param filename: The name of the file to upload
        :param path: The path of the file in the storage
        :return: The path of the uploaded file
        """
        pass

    @abstractmethod
    def list_all(self):
        """
        List all the files in the storage
        :return: The list of files in the storage
        """
        pass

    @abstractmethod
    def delete_file(self, path: str) -> bool:
        """
        Delete a file from the storage
        :param path: The path of the file in the storage
        """
        pass

    @abstractmethod
    def delete_folder(self, path: str) -> bool:
        """
        Delete a folder from the storage
        :param path: The path of the folder in the storage
        """
        pass
