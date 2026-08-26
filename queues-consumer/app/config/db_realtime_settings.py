from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Load the env file
load_dotenv()

@dataclass
class DBRealtimeSettings:
    """
    Class that holds all the relevant configuration to database
    """
    HOST: str = os.getenv("DB_REALTIME_HOST")
    PORT: str = os.getenv("DB_REALTIME_PORT", "5432")
    USER: str = os.getenv("DB_REALTIME_USERNAME")
    PASS: str = os.getenv("DB_REALTIME_PASSWORD")
    DB: str = os.getenv("DB_REALTIME_DATABASE")

    @property
    def connection_uri(self) -> str:
        return f"postgresql://{self.USER}:{self.PASS}@{self.HOST}:{self.PORT}/{self.DB}"

