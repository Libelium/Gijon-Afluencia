from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Load the env file
load_dotenv()

@dataclass
class SentrySettings:
    """
    Class that holds all the relevant configuration to database
    """
    DSN: str = os.getenv("SENTRY_DSN")
    TRACE_SAMPLE_RATE: str = os.getenv("SENTRY_TRACE_SAMPLE_RATE", "0")
    ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT")
