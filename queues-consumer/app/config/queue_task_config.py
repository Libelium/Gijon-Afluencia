import os
from dataclasses import dataclass

from dotenv import load_dotenv

from config.logging import appLogging as logging

load_dotenv()


@dataclass
class QueueTaskConfig:

    QUEUE_CONFIG_PREFIX: str = "QUEUE_TASK_CONFIG_"
    DEFAULT_CONFIG_PREFIX: str = f"{QUEUE_CONFIG_PREFIX}DEFAULT_"

    DEFAULT_PRIORITY: int = int(os.getenv(f"{DEFAULT_CONFIG_PREFIX}PRIORITY", 10))
    DEFAULT_TIMEOUT: int = int(os.getenv(f"{DEFAULT_CONFIG_PREFIX}TIMEOUT", 5))
    DEFAULT_MAX_RETRIES: int = int(os.getenv(f"{DEFAULT_CONFIG_PREFIX}MAX_RETRIES", 5))
    DEFAULT_RETRY_BACKOFF: int = int(
        os.getenv(f"{DEFAULT_CONFIG_PREFIX}RETRY_BACKOFF", 5)
    )

    def get_config_param(self, queue_name: str, param_name: str):
        """
        Returns the value of a parameter for a given queue name.
        If the parameter is not found, returns the default value.
        """

        queue_name = queue_name.upper().replace("-", "_").replace(".", "_")
        param_name = param_name.upper()

        var = os.getenv(
            f"{self.QUEUE_CONFIG_PREFIX}{queue_name}_{param_name}",
            getattr(self, f"DEFAULT_{param_name}"),
        )

        try:
            var = int(var)
        except ValueError:
            pass

        logging.info(f"QUEUE TASK CONFIG: {queue_name} {param_name} = {var}")

        return var
