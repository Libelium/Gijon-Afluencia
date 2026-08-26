from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

AVAILABLE_PROTOCOLS = {
    "amqp": "amqp",
    "amqps": "amqps"
}
@dataclass
class RabbitConfig:

    host: str = os.getenv("RABBITMQ_HOST", "")
    user: str = os.getenv("RABBITMQ_USER", "")
    password: str = os.getenv("RABBITMQ_PASSWORD", "")
    port: int = os.getenv("RABBITMQ_PORT", "")
    vhost: str = os.getenv("RABBITMQ_VHOST", "")
    security: str = os.getenv("RABBITMQ_SECURITY", "amqps")
    ca_file_path: str = os.getenv("RABBITMQ_CA_FILE_PATH", "")


    @property
    def connection_slug(self) -> str:
        return f"{self._protocol()}://{self._authority()}{self._vhost()}"

    def _protocol(self) -> str:
        if self.security in AVAILABLE_PROTOCOLS:
            return AVAILABLE_PROTOCOLS[self.security]
        else:
            raise ValueError(f"Protocol {self.security} not available")
    
    def _authority(self) -> str:
        return f"{self._userinfo()}@{self.host}:{self.port}"

    def _userinfo(self) -> str:
        return f"{self.user}:{self.password}"

    def _vhost(self) -> str:
        if self.vhost != "":
            return f"/{self.vhost}"
        return ""
