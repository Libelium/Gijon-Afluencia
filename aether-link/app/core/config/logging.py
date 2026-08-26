import logging
import sys
import os

# this variable is not in the config file
# because of circular imports, this was the 
# fastest way to solve the problem
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

if LOG_LEVEL == "DEBUG":
    logging_level = logging.DEBUG

elif LOG_LEVEL == "INFO":
    logging_level = logging.INFO

elif LOG_LEVEL == "WARNING":
    logging_level = logging.WARNING

elif LOG_LEVEL == "ERROR":
    logging_level = logging.ERROR

else:
    logging_level = logging.CRITICAL

logging.basicConfig(level=logging_level )

# Create a logger
root = logging.getLogger()
root.setLevel(logging_level)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging_level)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
root.addHandler(handler)

appLogging = logging
