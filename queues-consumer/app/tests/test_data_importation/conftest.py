import sys
from unittest.mock import MagicMock
import pytest

# Mock all heavy dependencies before they're imported anywhere
sys.modules['minio'] = MagicMock()
sys.modules['geoalchemy2'] = MagicMock()
sys.modules['config.local_storage'] = MagicMock()

# Mock tasks.sync to avoid loading heavy dependencies and Jinja templates
mock_tasks_sync = MagicMock()
mock_tasks_sync.save_timeseries_job = MagicMock()
mock_tasks_sync.save_realtime_job = MagicMock()
sys.modules['tasks.sync'] = mock_tasks_sync


@pytest.fixture(autouse=True)
def mock_all_deps(monkeypatch):
    """Automatically mock all heavy dependencies for all tests in this directory"""
    # This ensures the modules can import without errors
    pass
