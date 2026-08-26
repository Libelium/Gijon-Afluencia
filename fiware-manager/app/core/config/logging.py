import logging
import os
import sys

# Level is env-driven so raising verbosity doesn't need a rebuild. It defaults to
# INFO because DEBUG on the root logger also switches on urllib3/pymongo
# per-connection chatter, which is most of the log volume these pods produce.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
if LOG_LEVEL not in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"):
    LOG_LEVEL = "INFO"

# Create a logger
root = logging.getLogger()
root.setLevel(LOG_LEVEL)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(LOG_LEVEL)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s -[Uvicorn Worker ID: %(process)d] - [Thread ID: %(thread)d] - %(message)s"
)
handler.setFormatter(formatter)
root.addHandler(handler)

# Keep third-party chatter out of the way even when the app itself runs at DEBUG.
for noisy_logger in ("urllib3", "pymongo"):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

appLogging = logging
