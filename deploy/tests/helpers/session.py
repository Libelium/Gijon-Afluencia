"""
Shared state across test stages.

The suite is a pipeline: login produces a token, device creation produces a
device, later stages consume both. pytest fixtures cannot cross module
boundaries with this create-as-a-check pattern, so the stages share this tiny
store instead.

ORDERING CONTRACT: because this state is written by early stages and read by
later ones, the stages MUST run in file order (test_00 → test_06). That order
is enforced by conftest.pytest_collection_modifyitems; do not rely on pytest's
default collection order alone. Running a later stage in isolation is safe — it
skips as "blocked" via require() rather than failing on missing state.
"""

from typing import Optional

from .api import Device

token: Optional[str] = None
device: Optional[Device] = None
data_api_key: str = ""
