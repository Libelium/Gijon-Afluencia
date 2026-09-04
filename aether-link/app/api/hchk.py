import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config.config import healthchecks
from app.core.config.logging import appLogging as logging


router = APIRouter()

# total budget for the probe; the checks run in parallel, so it is also the
# per-dependency cap
HEALTHCHECK_TIMEOUT_SECONDS = 5.0

# one thread per dependency, reused across requests
_executor = ThreadPoolExecutor(
    max_workers=max(len(healthchecks), 1), thread_name_prefix="hchk"
)

# reusing the pending future keeps a hung backend from taking one thread per probe
# until the pool is exhausted and healthy backends are reported as down
_inflight: dict[str, Future] = {}
_inflight_lock = threading.Lock()


@router.get("/hchk")
def test():
    """
    Check the three configured backends (data source, context broker and IoT
    agent): 200 if they all answer, 503 if any of them fails or times out.
    """

    futures = {
        name: _submit(name, service) for name, service in healthchecks.items()
    }

    errors = []
    deadline = time.monotonic() + HEALTHCHECK_TIMEOUT_SECONDS

    for name, future in futures.items():
        try:
            if not future.result(timeout=max(deadline - time.monotonic(), 0)):
                errors.append(name)
        except FutureTimeoutError:
            errors.append(f"{name} (timeout)")
        except Exception as e:
            logging.error(f"Error checking health of {name}: {e}")
            errors.append(name)

    if errors:
        logging.error(f"Error checking health: {errors}")
        return JSONResponse(
            status_code=503,
            content=f"ERROR: the following services are down: {', '.join(errors)}",
        )

    return "OK"


def _submit(name: str, service) -> Future:
    with _inflight_lock:
        future = _inflight.get(name)
        if future is None or future.done():
            future = _executor.submit(_check_service, service)
            _inflight[name] = future
        return future


def _check_service(service) -> bool:
    # a backend that did not load at startup is left as None in `healthchecks`
    return bool(service.health_check()) if service else False


# liveness only says the process answers: a liveness probe that depended on the
# backends would have kubelet kill this service whenever one of them goes down
@router.get("/alive")
async def alive():
    # async on purpose: it touches no dependency, so on the event loop it does not
    # queue behind the synchronous handlers and time out
    return "OK"
