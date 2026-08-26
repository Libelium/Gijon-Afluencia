from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Load the env file
load_dotenv()


@dataclass
class LocalStorageSettings:
    """
    Class that holds all the relevant configuration to S3 connection
    """

    ACCESS_ID: str = os.getenv("LOCAL_ACCESS_ID")
    SECRET_KEY: str = os.getenv("LOCAL_SECRET_KEY")
    ENDPOINT: str = os.getenv("LOCAL_ENDPOINT")
    BUCKET: str = os.getenv("LOCAL_BUCKET")
    SECURE: bool = os.getenv("LOCAL_SECURE", "false") == "true"
    FILES_PATH = os.getenv("FILES_PATH", "temp_files")


@dataclass
class LocalImageStorageSettings:
    """
    Class that holds all the relevant configuration to S3 connection
    """

    ACCESS_ID: str = os.getenv("LOCAL_IMAGES_ACCESS_ID")
    SECRET_KEY: str = os.getenv("LOCAL_IMAGES_SECRET_KEY")
    ENDPOINT: str = os.getenv("LOCAL_IMAGES_ENDPOINT")
    BUCKET: str = os.getenv("LOCAL_IMAGES_BUCKET")
    SECURE: bool = os.getenv("LOCAL_IMAGES_SECURE", "false") == "true"
    FILES_PATH = os.getenv("FILES_PATH", "temp_files")
