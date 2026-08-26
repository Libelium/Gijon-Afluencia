from dataclasses import dataclass


@dataclass
class DBSettings:
    """
    Class that holds all the relevant configuration to database
    """

    HOST: str
    PORT: str
    USER: str
    PASS: str
    DB: str
    POOL_SIZE: int

    @property
    def connection_uri(self) -> str:
        return f"postgresql://{self.USER}:{self.PASS}@{self.HOST}:{self.PORT}/{self.DB}"
