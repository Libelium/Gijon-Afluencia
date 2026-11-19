"""
Beat routes a periodic task to its queue only if its process imported the task
module. A cb_processor process does not know the crowd tasks.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[2]
TASK = "platform.crowd.process_visitors_all_job"

PROBE = f"""
import json
from config.celery import app
task = app.tasks.get("{TASK}")
print(json.dumps(task.queue if task else None))
"""


def registered_queue(worker_type: str):
    result = subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=APP_DIR,
        env={**os.environ, "WORKER_TYPE": worker_type, "PYTHONPATH": str(APP_DIR)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


class TestBeatTaskRouting:
    def test_cb_processor_does_not_know_the_crowd_tasks(self):
        assert registered_queue("cb_processor") is None

    @pytest.mark.parametrize("worker_type", ["universal", "generic_processor"])
    def test_full_worker_types_route_crowd_to_its_queue(self, worker_type):
        assert registered_queue(worker_type) == "platform.crowd.process_visitors_all"
