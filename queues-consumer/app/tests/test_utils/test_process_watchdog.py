"""
Test for helpers.process_watchdog: the parent must die when a celery child
(worker or beat) dies, so Kubernetes restarts the pod.
"""

import threading
from unittest.mock import MagicMock, patch

from helpers import process_watchdog as wd


class FakeProcess:
    """Minimal Popen stand-in: poll() returns None while alive."""

    def __init__(self, returncode=None):
        self.returncode = returncode
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.returncode = -9


class TestFindDeadProcess:
    def test_returns_none_when_all_alive(self):
        processes = [("worker-0", FakeProcess()), ("beat", FakeProcess())]
        assert wd.find_dead_process(processes) is None

    def test_returns_first_dead_process_with_its_code(self):
        processes = [
            ("worker-0", FakeProcess()),
            ("beat", FakeProcess(returncode=137)),
            ("worker-1", FakeProcess(returncode=1)),
        ]
        assert wd.find_dead_process(processes) == ("beat", 137)


class TestTerminateProcesses:
    def test_only_signals_alive_processes(self):
        alive = FakeProcess()
        dead = FakeProcess(returncode=0)
        terminated = wd.terminate_processes([("worker-0", alive), ("beat", dead)])
        assert terminated == ["worker-0"]
        assert alive.terminated is True
        assert dead.terminated is False


class TestWatchProcesses:
    def test_calls_handler_once_and_returns_when_a_process_dies(self):
        beat = FakeProcess()
        processes = [("worker-0", FakeProcess()), ("beat", beat)]
        handler = MagicMock()

        polls = {"n": 0}
        original_poll = beat.poll

        def poll_then_die():
            polls["n"] += 1
            if polls["n"] >= 3:
                beat.returncode = 137
            return original_poll()

        beat.poll = poll_then_die

        result = wd.watch_processes(processes, poll_interval=0, on_death=handler)

        assert result == ("beat", 137)
        handler.assert_called_once_with("beat", 137)

    def test_stop_event_ends_the_loop_without_calling_handler(self):
        processes = [("worker-0", FakeProcess())]
        handler = MagicMock()
        stop = threading.Event()
        stop.set()

        assert (
            wd.watch_processes(
                processes, poll_interval=0, on_death=handler, stop_event=stop
            )
            is None
        )
        handler.assert_not_called()


class TestExitOnDeath:
    def test_terminates_siblings_and_exits_non_zero(self):
        worker = FakeProcess()
        beat = FakeProcess(returncode=137)
        processes = [("worker-0", worker), ("beat", beat)]

        with patch.object(wd.os, "_exit") as fake_exit:
            wd.exit_on_death(processes)("beat", 137)

        fake_exit.assert_called_once_with(1)
        assert worker.terminated is True
        assert beat.terminated is False

    def test_watch_processes_uses_exit_handler_by_default(self):
        processes = [("beat", FakeProcess(returncode=1))]
        with patch.object(wd.os, "_exit") as fake_exit:
            assert wd.watch_processes(processes, poll_interval=0) == ("beat", 1)
        fake_exit.assert_called_once_with(1)


class TestStartProcessWatchdog:
    def test_starts_a_daemon_thread_that_reacts_to_death(self):
        beat = FakeProcess()
        processes = [("beat", beat)]
        handler_calls = []

        def fake_watch(processes, poll_interval, stop_event=None):
            handler_calls.append((processes, poll_interval))

        with patch.object(wd, "watch_processes", side_effect=fake_watch):
            thread = wd.start_process_watchdog(processes, poll_interval=0.01)
            thread.join(timeout=1)

        assert thread.daemon is True
        assert thread.name == "process-watchdog"
        assert handler_calls == [([("beat", beat)], 0.01)]


class TestStopProcesses:
    def test_signals_every_live_process_and_waits_for_it(self):
        worker, beat = FakeProcess(), FakeProcess()

        killed = wd.stop_processes([("worker-0", worker), ("beat", beat)], timeout=5)

        assert worker.terminated and beat.terminated
        assert killed == []

    def test_kills_what_does_not_stop_in_time(self):
        import subprocess

        stuck = MagicMock()
        stuck.poll.return_value = None
        stuck.wait.side_effect = subprocess.TimeoutExpired("celery", 0.01)

        killed = wd.stop_processes([("worker-0", stuck)], timeout=0.01)

        stuck.terminate.assert_called_once()
        stuck.kill.assert_called_once()
        assert killed == ["worker-0"]


class TestStoppingIsNotADeath:
    def test_a_child_that_exits_while_the_pod_stops_does_not_exit_the_parent(self):
        # Set between the loop check and the poll that sees the child gone.
        stopping = MagicMock()
        stopping.is_set.side_effect = [False, True]
        handler = MagicMock()

        result = wd.watch_processes([("worker-0", FakeProcess(returncode=0))], poll_interval=0, on_death=handler, stop_event=stopping)

        assert result is None
        handler.assert_not_called()


class TestStopProcessesForReal:
    def test_a_real_child_gets_sigterm_and_its_time_to_flush(self, tmp_path):
        import subprocess
        import sys

        flushed = tmp_path / "flushed"
        child = subprocess.Popen([
            sys.executable, "-c",
            "import signal, sys, time\n"
            "def stop(*_):\n"
            "    time.sleep(0.3)\n"
            f"    open({str(flushed)!r}, 'w').write('ok')\n"
            "    sys.exit(0)\n"
            "signal.signal(signal.SIGTERM, stop)\n"
            "print('ready', flush=True)\n"
            "time.sleep(60)\n",
        ], stdout=subprocess.PIPE, text=True)
        child.stdout.readline()

        killed = wd.stop_processes([("worker-0", child)], timeout=5)

        assert killed == []
        assert child.returncode == 0
        assert flushed.read_text() == "ok"
