"""
Exits main.py when one of its celery children (workers or beat) dies, so
Kubernetes restarts the pod instead of leaving it Running without them.
Also stops them in order when the pod is told to stop.
"""

import os
import threading
import time
from typing import Callable, List, Optional, Sequence, Tuple

from config.logging import appLogging as logging

DEFAULT_POLL_INTERVAL_SECONDS = 5.0
EXIT_CODE_ON_CHILD_DEATH = 1

NamedProcess = Tuple[str, object]
DeathHandler = Callable[[str, int], None]


def find_dead_process(processes: Sequence[NamedProcess]) -> Optional[Tuple[str, int]]:
    """
    Returns (name, returncode) of the first process that has exited,
    or None when every process is still alive.
    """
    for name, process in processes:
        returncode = process.poll()
        if returncode is not None:
            return name, returncode
    return None


def terminate_processes(processes: Sequence[NamedProcess]) -> List[str]:
    """
    Sends SIGTERM to every process that is still alive. Returns the names
    of the processes that were signalled.
    """
    terminated = []
    for name, process in processes:
        if process.poll() is None:
            try:
                process.terminate()
                terminated.append(name)
            except Exception as e:
                logging.warning(f"Could not terminate {name}: {e}")
    return terminated


def stop_processes(processes: Sequence[NamedProcess], timeout: float) -> List[str]:
    """
    SIGTERM to every live process, so celery shuts down warm: running tasks
    finish and each child runs its shutdown hooks (worker_process_shutdown),
    then waits for them up to `timeout` seconds and kills what is left.
    Returns the names killed.
    """
    terminate_processes(processes)
    deadline = time.monotonic() + timeout
    killed = []
    for name, process in processes:
        try:
            process.wait(timeout=max(0.0, deadline - time.monotonic()))
        except Exception:
            try:
                process.kill()
                killed.append(name)
            except Exception as e:
                logging.warning(f"Could not kill {name}: {e}")
    return killed


def exit_on_death(processes: Sequence[NamedProcess]) -> DeathHandler:
    """
    Default death handler: log, terminate the siblings and exit the parent
    with a non-zero code.
    """

    def handler(name: str, returncode: int) -> None:
        logging.critical(
            f"Child process '{name}' exited with code {returncode}; "
            "terminating the remaining processes and exiting so the pod restarts"
        )
        terminated = terminate_processes(processes)
        if terminated:
            logging.info(f"Terminated: {', '.join(terminated)}")
        # sys.exit would only stop this thread; uvicorn owns the main one
        os._exit(EXIT_CODE_ON_CHILD_DEATH)

    return handler


def watch_processes(
    processes: Sequence[NamedProcess],
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    on_death: Optional[DeathHandler] = None,
    stop_event: Optional[threading.Event] = None,
) -> Optional[Tuple[str, int]]:
    """
    Blocks polling `processes` every `poll_interval` seconds. When one of
    them exits, calls `on_death(name, returncode)` and returns that tuple.
    Returns None only if `stop_event` is set before any process dies.
    """
    handler = on_death or exit_on_death(processes)
    while stop_event is None or not stop_event.is_set():
        dead = find_dead_process(processes)
        # A child that exits because the pod is stopping is not a death.
        if dead is not None and stop_event is not None and stop_event.is_set():
            return None
        if dead is not None:
            handler(*dead)
            return dead
        time.sleep(poll_interval)
    return None


def start_process_watchdog(
    processes: Sequence[NamedProcess],
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    stop_event: Optional[threading.Event] = None,
) -> threading.Thread:
    """
    Starts the watchdog in a daemon thread and returns it.
    """
    names = ", ".join(name for name, _ in processes)
    logging.info(f"Starting process watchdog over: {names}")
    thread = threading.Thread(
        target=watch_processes,
        kwargs={"processes": list(processes), "poll_interval": poll_interval, "stop_event": stop_event},
        name="process-watchdog",
        daemon=True,
    )
    thread.start()
    return thread
