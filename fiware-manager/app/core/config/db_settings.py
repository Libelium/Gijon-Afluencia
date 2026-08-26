from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Load the env file
load_dotenv()


@dataclass
class MongoDbSettings:
    """
    Class that holds all the relevant configuration to mongodb database
    """

    HOST: str = os.getenv("MONGO_DB_HOST", "")
    USER: str = os.getenv("MONGO_DB_USERNAME", "")
    PASS: str = os.getenv("MONGO_DB_PASSWORD", "")
    DB: str = os.getenv("MONGO_DB_DATABASE", "")
    PORT: int = os.getenv("MONGO_DB_PORT", 0)

    @property
    def CONNECTION_URI(self):
        if self.USER == "" or self.PASS == "":
            return f"mongodb://{self.HOST}:{self.PORT}/"
        return f"mongodb://{self.USER}:{self.PASS}@{self.HOST}:{self.PORT}/"
