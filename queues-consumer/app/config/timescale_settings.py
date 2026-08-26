from dataclasses import dataclass
import os
from typing import List
from dotenv import load_dotenv
from config.logging import appLogging as logging

load_dotenv()


@dataclass
class TimescaleSettings:
    """
    Class that holds all the relevant configuration to timescale database
    """

    HOST: str
    PORT: str
    USER: str
    PASS: str
    DB: str

    @property
    def connection_uri(self) -> str:
        return f"postgresql://{self.USER}:{self.PASS}@{self.HOST}:{self.PORT}/{self.DB}"

    def __post_init__(self):
        if not all([self.HOST, self.PORT, self.USER, self.PASS, self.DB]):
            raise ValueError("All fields must be set: HOST, PORT, USER, PASS, DB")


class TimescaleDbsSettings:
    """
    This class holds the configuration of an array of timescale databases,
    each being a TimescaleSettings object.
    """

    def __init__(self):
        """
        Load all configured databases
        """

        self.dbs: List[TimescaleSettings] = []

        try:

            self.__load_default_db()
            self.__load_extra_dbs()

        except Exception as e:
            logging.error(
                f"Error loading timescale databases from environment variables: {e}"
            )

    def __load_default_db(self):
        """
        Load the default database from environment variables
        """
        db = TimescaleSettings(
            HOST=os.getenv("TS_DB_HOST"),
            PORT=os.getenv("TS_DB_PORT", "5432"),
            USER=os.getenv("TS_DB_USERNAME"),
            PASS=os.getenv("TS_DB_PASSWORD"),
            DB=os.getenv("TS_DB_DATABASE"),
        )

        self.dbs.append(db)

    def __load_extra_dbs(self):
        """
        Load all extra databases from environment variables,
        with the prefix TS_DB_1, TS_DB_2, ...
        Prexises must be ordered and start from 1, if there is a gap,
        the loading will stop in the first gap.
        The same applies if there is an error in the environment variable,
        The loading will stop in the first error.
        """

        idx = 1

        while True:

            host = os.getenv(f"TS_DB_{idx}_HOST")

            if not host:
                # No more databases to load
                break

            port = os.getenv(f"TS_DB_{idx}_PORT", "5432")
            user = os.getenv(f"TS_DB_{idx}_USERNAME")
            password = os.getenv(f"TS_DB_{idx}_PASSWORD")
            database = os.getenv(f"TS_DB_{idx}_DATABASE")

            self.dbs.append(
                TimescaleSettings(
                    HOST=host,
                    PORT=port,
                    USER=user,
                    PASS=password,
                    DB=database,
                )
            )

            idx += 1

    def get_dbs(self):
        """
        Returns the list of timescale databases
        """
        return self.dbs
