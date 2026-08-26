from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Load the env file
load_dotenv()

@dataclass
class GeneralConfig:
    """
    Class with the general configuration of the queue consumer process
    """
    QUEUE_CONSUMER_WORKERS: int = int(os.getenv("QUEUE_CONSUMER_WORKERS") or 1)
    AETHER_LINK_URL: str = os.getenv("AETHER_LINK_URL")