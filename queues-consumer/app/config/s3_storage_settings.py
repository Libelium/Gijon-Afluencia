from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Load the env file
load_dotenv()


@dataclass
class S3StorageSettings:
    """
    Class that holds all the relevant configuration to S3 connection
    """

    ACCESS_ID: str = os.getenv("AWS_S3_ACCESS_ID")
    SECRET_KEY: str = os.getenv("AWS_S3_SECRET_KEY")
    REGION: str = os.getenv("AWS_S3_REGION")
    BUCKET: str = os.getenv("AWS_S3_BUCKET")
    FILES_PATH = os.getenv("FILES_PATH", "temp_files")

@dataclass
class S3ImageStorageSettings:
    """
    Class that holds all the relevant configuration to S3 connection
    """

    ACCESS_ID: str = os.getenv("AWS_S3_IMAGES_ACCESS_ID")
    SECRET_KEY: str = os.getenv("AWS_S3_IMAGES_SECRET_KEY")
    REGION: str = os.getenv("AWS_S3_IMAGES_REGION")
    BUCKET: str = os.getenv("AWS_S3_IMAGES_BUCKET")
    FILES_PATH = os.getenv("FILES_PATH", "temp_files")

