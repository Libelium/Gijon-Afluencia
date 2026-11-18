"""
Tests that main.py hands every celery child (workers and beat) to the
process watchdog.
"""

import runpy
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config.config import settings
from config.queue_worker_type import WorkerType

MAIN_PATH = Path(__file__).resolve().parents[2] / "main.py"


def _run_main(
    num_workers: int,
    launch_scheduler: bool,
    worker_type: WorkerType = WorkerType.UNIVERSAL,
):
    """
    Executes main.py as __main__ with process spawning, sleeps and uvicorn
    stubbed out. Returns (spawned processes, start_process_watchdog mock).
    """
    spawned = []

    def fake_popen(args, **kwargs):
        process = MagicMock(name=" ".join(args))
        process.args = args
        process.env = kwargs.get("env")
        spawned.append(process)
        return process

    with (
        patch.object(settings, "PROMETHEUS_MULTIPROC_DIR", None),
        patch.object(settings, "WORKER_TYPE", worker_type),
        patch.object(settings, "QUEUE_CONSUMER_WORKERS", num_workers),
        patch.object(settings, "LAUNCH_CELERY_SCHEDULER", launch_scheduler),
        patch.object(settings, "LAUNCH_UVICORN", False),
        patch("subprocess.Popen", side_effect=fake_popen),
        patch("time.sleep"),
        patch("helpers.process_watchdog.start_process_watchdog") as start_watchdog,
        patch("signal.signal"),
    ):
        runpy.run_path(str(MAIN_PATH), run_name="__main__")

    return spawned, start_watchdog


class TestMainWatchdogWiring:
    def test_watches_every_worker_and_beat(self):
        spawned, start_watchdog = _run_main(num_workers=2, launch_scheduler=True)

        start_watchdog.assert_called_once()
        (watched,), _ = start_watchdog.call_args
        assert [name for name, _ in watched] == ["worker-0", "worker-1", "beat"]
        assert [process for _, process in watched] == spawned
        assert "beat" in spawned[-1].args

    def test_watches_workers_only_when_scheduler_disabled(self):
        spawned, start_watchdog = _run_main(num_workers=1, launch_scheduler=False)

        (watched,), _ = start_watchdog.call_args
        assert watched == [("worker-0", spawned[0])]
        assert all("beat" not in p.args for p in spawned)

    @pytest.mark.parametrize("launch_scheduler", [True, False])
    def test_watchdog_starts_before_uvicorn_blocks(self, launch_scheduler):
        calls = []
        with (
            patch("uvicorn.run", side_effect=lambda *a, **k: calls.append("uvicorn")),
            patch.object(settings, "LAUNCH_UVICORN", True),
            patch.object(settings, "PROMETHEUS_MULTIPROC_DIR", None),
            patch.object(settings, "WORKER_TYPE", WorkerType.UNIVERSAL),
            patch.object(settings, "QUEUE_CONSUMER_WORKERS", 1),
            patch.object(settings, "LAUNCH_CELERY_SCHEDULER", launch_scheduler),
            patch("subprocess.Popen", return_value=MagicMock()),
            patch("time.sleep"),
            patch(
                "helpers.process_watchdog.start_process_watchdog",
                side_effect=lambda *a, **k: calls.append("watchdog"),
            ),
            patch(
                "helpers.process_watchdog.stop_processes",
                side_effect=lambda *a, **k: calls.append("stop") or [],
            ),
            patch("signal.signal"),
        ):
            runpy.run_path(str(MAIN_PATH), run_name="__main__")

        # uvicorn returns on SIGTERM, and then celery is stopped in order.
        assert calls == ["watchdog", "uvicorn", "stop"]


class TestBeatLoadsEveryTask:
    def test_beat_runs_as_universal_whatever_the_pod_worker_type(self):
        spawned, _ = _run_main(
            num_workers=2, launch_scheduler=True, worker_type=WorkerType.CB_PROCESSOR
        )

        beat, workers = spawned[-1], spawned[:-1]
        assert "beat" in beat.args
        assert beat.env["WORKER_TYPE"] == WorkerType.UNIVERSAL.value
        assert all(worker.env is None for worker in workers)


def _worker_names(spawned) -> list[str]:
    return [p.args[p.args.index("-n") + 1] for p in spawned if "worker" in p.args]


class TestWorkerNames:
    """
    The chart fixes the pod hostname, so %h is the same in every pod of a deployment. Two pods alive at
    once during a rollout must not share a worker name, or the new one dies on the exclusive pidbox queue.
    """

    def test_two_starts_never_share_a_worker_name(self, monkeypatch):
        monkeypatch.delenv("POD_NAME", raising=False)

        first = _worker_names(_run_main(num_workers=2, launch_scheduler=False)[0])
        second = _worker_names(_run_main(num_workers=2, launch_scheduler=False)[0])

        assert len(set(first)) == 2
        assert not set(first) & set(second)
        assert all(name.startswith("worker@%h-") for name in first + second)

    def test_the_pod_name_is_used_when_kubernetes_provides_it(self, monkeypatch):
        monkeypatch.setenv("POD_NAME", "cb-consumer-6996969f59-d22zx")

        names = _worker_names(_run_main(num_workers=2, launch_scheduler=False)[0])

        assert names == [
            "worker@%h-cb-consumer-6996969f59-d22zx-0",
            "worker@%h-cb-consumer-6996969f59-d22zx-1",
        ]


class TestShutdown:
    """Kubernetes signals main.py only: it has to pass SIGTERM on so celery stops in order."""

    def _handlers(self, launch_uvicorn=False):
        handlers = {}
        with (
            patch.object(settings, "PROMETHEUS_MULTIPROC_DIR", None),
            patch.object(settings, "WORKER_TYPE", WorkerType.UNIVERSAL),
            patch.object(settings, "QUEUE_CONSUMER_WORKERS", 2),
            patch.object(settings, "LAUNCH_CELERY_SCHEDULER", False),
            patch.object(settings, "LAUNCH_UVICORN", launch_uvicorn),
            patch("subprocess.Popen", side_effect=lambda *a, **k: MagicMock()),
            patch("time.sleep"),
            patch("helpers.process_watchdog.start_process_watchdog") as start_watchdog,
            patch("helpers.process_watchdog.stop_processes", return_value=[]) as stop,
            patch("signal.signal", side_effect=lambda sig, handler: handlers.__setitem__(sig, handler)),
        ):
            runpy.run_path(str(MAIN_PATH), run_name="__main__")
            return handlers, stop, start_watchdog

    def test_sigterm_stops_every_child_within_the_grace_and_exits_cleanly(self):
        import signal

        handlers, stop, _ = self._handlers()

        with pytest.raises(SystemExit) as exit_info:
            handlers[signal.SIGTERM](signal.SIGTERM, None)

        assert exit_info.value.code == 0
        (watched, grace), _ = stop.call_args
        assert [name for name, _ in watched] == ["worker-0", "worker-1"]
        assert grace == settings.SHUTDOWN_GRACE_SECONDS

    def test_the_watchdog_is_told_when_the_pod_is_stopping(self):
        import signal

        handlers, _, start_watchdog = self._handlers()
        stopping = start_watchdog.call_args.kwargs["stop_event"]
        assert not stopping.is_set()

        with pytest.raises(SystemExit):
            handlers[signal.SIGTERM](signal.SIGTERM, None)

        assert stopping.is_set()
