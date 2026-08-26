"""
Worker types and their associated queue/task-module combinations.
"""

from enum import Enum

_ALL_TASK_MODULES = [
    "tasks.sync",
    "tasks.data",
    "tasks.crowd",
    "tasks.data_cache",
]


class WorkerType(str, Enum):
    # --- Domain workers (each handles a single domain) ---
    SYNC = "sync"
    DATA = "data"
    CROWD = "crowd"
    DATA_CACHE = "data_cache"

    # --- Aggregate workers (combine multiple domains) ---
    CORE = "core"
    UNIVERSAL = "universal"
    UNIVERSAL_ON_PREMISE = "universal_on_premise"
    CUSTOM = "custom"

    # --- Infrastructure workers ---
    CB_PROCESSOR = "cb_processor"
    GENERIC_PROCESSOR = "generic_processor"
    DLQ_RECOVERY = "dlq_recovery"

    def get_queues(self):
        # Imported here to avoid circular imports
        import config.queues as q

        mapping = {
            # Domain workers
            WorkerType.SYNC:            q.SYNC_QUEUES,
            WorkerType.DATA:            q.DATA_QUEUES,
            WorkerType.CROWD:           q.CROWD_QUEUES,
            WorkerType.DATA_CACHE:      q.DATA_CACHE_QUEUES,
            # Aggregate workers
            WorkerType.CORE: q.SYNC_QUEUES + q.DATA_QUEUES,
            WorkerType.UNIVERSAL: q.ALL_QUEUES,
            WorkerType.UNIVERSAL_ON_PREMISE: [
                queue for queue in q.ALL_QUEUES
                if queue not in q.NOT_NEEDED_ON_PREMISE_QUEUES
            ],
            WorkerType.CUSTOM: q.CUSTOM_QUEUES,
            # Infrastructure workers
            WorkerType.CB_PROCESSOR:      [q.SYNC_CB_NOTIFICATION_QUEUE],
            WorkerType.GENERIC_PROCESSOR: [
                queue for queue in q.ALL_QUEUES
                if queue != q.SYNC_CB_NOTIFICATION_QUEUE
            ],
            WorkerType.DLQ_RECOVERY: [],
        }

        if self not in mapping:
            raise ValueError(f"Consumer type {self} not recognized")

        return mapping[self]

    def get_task_modules(self) -> list[str]:
        """Returns the task module names that must be loaded for this worker type."""
        return _TASK_MODULE_MAP.get(self, _ALL_TASK_MODULES)

    def get_preload_modules(self) -> tuple[str, ...]:
        """Returns the heavy third-party modules to pre-import before workers are forked."""
        return _PRELOAD_MAP.get(self, _COMMON)


_DATA        = ("numpy", "pandas")
_SPREADSHEET = ("openpyxl",)
_COMMON      = ("jinja2", "pika", "requests")

_PRELOAD_MAP: dict[WorkerType, tuple[str, ...]] = {
    # Domain workers
    WorkerType.SYNC:              _COMMON,
    WorkerType.DATA:              _COMMON + _DATA + _SPREADSHEET,
    WorkerType.CROWD:             _COMMON + _DATA,
    WorkerType.DATA_CACHE:        _COMMON + _DATA,
    # Aggregate workers
    WorkerType.CORE:              _COMMON + _DATA + _SPREADSHEET,
    WorkerType.UNIVERSAL:         _COMMON + _DATA + _SPREADSHEET,
    WorkerType.UNIVERSAL_ON_PREMISE: _COMMON + _DATA + _SPREADSHEET,
    WorkerType.CUSTOM:            _COMMON + _DATA + _SPREADSHEET,
    # Infrastructure workers
    WorkerType.CB_PROCESSOR:      _COMMON,
    WorkerType.GENERIC_PROCESSOR: _COMMON + _DATA + _SPREADSHEET,
    WorkerType.DLQ_RECOVERY:      (),
}


_TASK_MODULE_MAP: dict[WorkerType, list[str]] = {
    # Domain workers
    WorkerType.SYNC:             ["tasks.sync"],
    WorkerType.DATA:             ["tasks.data"],
    WorkerType.CROWD:            ["tasks.crowd"],
    WorkerType.DATA_CACHE:       ["tasks.data_cache"],
    # Aggregate workers
    WorkerType.CORE:             ["tasks.sync", "tasks.data"],
    WorkerType.UNIVERSAL:             _ALL_TASK_MODULES,
    WorkerType.UNIVERSAL_ON_PREMISE:  _ALL_TASK_MODULES,
    WorkerType.CUSTOM:                _ALL_TASK_MODULES,
    # Infrastructure workers
    WorkerType.CB_PROCESSOR:      ["tasks.sync"],
    WorkerType.GENERIC_PROCESSOR: _ALL_TASK_MODULES,
    WorkerType.DLQ_RECOVERY:      [],
}
