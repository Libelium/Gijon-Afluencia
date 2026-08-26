import os
import multiprocessing

from dotenv import load_dotenv

# Optional operator overrides. The file does not need to exist: every setting
# has a default below. See gunicorn/.env.example.
load_dotenv("gunicorn/.env")

# How many workers should we use?
# https://docs.gunicorn.org/en/stable/design.html#how-many-workers
DEFAULTS = {
    "GUNICORN_BIND": "0.0.0.0:8000",
    "GUNICORN_WORKERS": str((multiprocessing.cpu_count() * 2) + 1),
    # Best performance workers https://stackoverflow.com/a/63427961
    "GUNICORN_WORKER_CLASS": "uvicorn.workers.UvicornWorker",
    # eliminate worker timeout
    "GUNICORN_TIMEOUT": "0",
    "GUNICORN_LOGLEVEL": "info",
    "GUNICORN_RELOAD": "false",
}

for name, value in DEFAULTS.items():
    os.environ.setdefault(name, value)

# Every GUNICORN_<SETTING> becomes the gunicorn <setting> config value
for k, v in list(os.environ.items()):
    if k.startswith("GUNICORN_"):
        key = k.split('_', 1)[1].lower()
        locals()[key] = v
