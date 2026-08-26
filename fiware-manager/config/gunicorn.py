import os
import resource
import multiprocessing
from dotenv import load_dotenv


load_dotenv("config/.env")

# Gunicorn aborts (SIGABRT) any worker that misses its heartbeat. With the
# default RLIMIT_CORE every abort dumped a ~300 MB core into the WORKDIR, which
# filled the node's ephemeral storage and got the whole pod evicted. The dumps
# are of no use to us, so drop the limit for the arbiter and every worker it
# forks from here.
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

# How many workers should use ?
# https://docs.gunicorn.org/en/stable/design.html#how-many-workers
if not os.environ.get('GUNICORN_WORKERS'):
    os.environ['GUNICORN_WORKERS'] = str((multiprocessing.cpu_count() * 2) + 1)

# Gunicorn's default is 30s, which is below the worst-case round trip to the IoT
# Agent / Orion, so workers doing real work were being killed as if hung.
if not os.environ.get('GUNICORN_TIMEOUT'):
    os.environ['GUNICORN_TIMEOUT'] = '120'

# `and v` because env-example ships these keys blank: an empty value must fall
# through to gunicorn's own default, not be passed on as "" and fail validation.
for k, v in os.environ.items():
    if k.startswith("GUNICORN_") and v:
        key = k.split('_', 1)[1].lower()
        locals()[key] = v
