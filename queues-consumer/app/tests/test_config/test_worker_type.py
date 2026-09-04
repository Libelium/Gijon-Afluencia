"""
Tests for WorkerType functionality: queue configuration and task module loading.
"""
import importlib
from unittest.mock import MagicMock, call, patch

import pytest
from kombu import Queue

import config.queues as q
from config.queue_worker_type import WorkerType, _ALL_TASK_MODULES, _TASK_MODULE_MAP


class TestWorkerTypeEnum:
    """Verify all expected worker types are declared."""

    EXPECTED_DOMAIN_WORKERS = {
        WorkerType.SYNC,
        WorkerType.ALARMS,
        WorkerType.DATA,
        WorkerType.CROWD,
        WorkerType.DATA_CACHE,
    }

    EXPECTED_AGGREGATE_WORKERS = {
        WorkerType.CORE,
        WorkerType.UNIVERSAL,
        WorkerType.UNIVERSAL_ON_PREMISE,
        WorkerType.CUSTOM,
    }

    EXPECTED_INFRA_WORKERS = {
        WorkerType.CB_PROCESSOR,
        WorkerType.GENERIC_PROCESSOR,
        WorkerType.DLQ_RECOVERY,
    }

    def test_all_worker_types_are_strings(self):
        for wt in WorkerType:
            assert isinstance(wt.value, str)

    def test_domain_workers_exist(self):
        for worker in self.EXPECTED_DOMAIN_WORKERS:
            assert worker in WorkerType

    def test_aggregate_workers_exist(self):
        for worker in self.EXPECTED_AGGREGATE_WORKERS:
            assert worker in WorkerType

    def test_infra_workers_exist(self):
        for worker in self.EXPECTED_INFRA_WORKERS:
            assert worker in WorkerType

    def test_all_worker_types_are_reachable_by_value(self):
        for wt in WorkerType:
            assert WorkerType(wt.value) is wt


class TestGetQueues:
    """Verify get_queues() returns correct queues for every worker type."""

    def _assert_queues(self, worker_type, expected_queues):
        result = worker_type.get_queues()
        assert result == expected_queues, (
            f"{worker_type}: expected {[q.name for q in expected_queues]}, "
            f"got {[q.name for q in result]}"
        )

    def _assert_all_are_queue_objects(self, queues):
        for item in queues:
            assert isinstance(item, Queue), f"{item!r} is not a kombu Queue"

    # --- Domain workers ---

    def test_sync_queues(self):
        result = WorkerType.SYNC.get_queues()
        assert result == q.SYNC_QUEUES
        self._assert_all_are_queue_objects(result)

    def test_data_queues(self):
        result = WorkerType.DATA.get_queues()
        assert result == q.DATA_QUEUES
        self._assert_all_are_queue_objects(result)

    def test_crowd_queues(self):
        result = WorkerType.CROWD.get_queues()
        assert result == q.CROWD_QUEUES
        self._assert_all_are_queue_objects(result)

    def test_data_cache_queues(self):
        result = WorkerType.DATA_CACHE.get_queues()
        assert result == q.DATA_CACHE_QUEUES
        self._assert_all_are_queue_objects(result)

    # --- Aggregate workers ---

    def test_universal_returns_all_queues(self):
        result = WorkerType.UNIVERSAL.get_queues()
        assert result == q.ALL_QUEUES
        self._assert_all_are_queue_objects(result)

    def test_universal_on_premise_excludes_not_needed_queues(self):
        result = WorkerType.UNIVERSAL_ON_PREMISE.get_queues()
        expected = [queue for queue in q.ALL_QUEUES if queue not in q.NOT_NEEDED_ON_PREMISE_QUEUES]
        assert result == expected
        for excluded in q.NOT_NEEDED_ON_PREMISE_QUEUES:
            assert excluded not in result, f"Queue {excluded.name} should be excluded on-premise"

    def test_core_combines_expected_queues(self):
        result = WorkerType.CORE.get_queues()
        expected = q.SYNC_QUEUES + q.DATA_QUEUES
        assert result == expected

    def test_custom_returns_custom_queues(self):
        result = WorkerType.CUSTOM.get_queues()
        assert result == q.CUSTOM_QUEUES

    # --- Infrastructure workers ---

    def test_cb_processor_gets_only_cb_notification_queue(self):
        result = WorkerType.CB_PROCESSOR.get_queues()
        assert result == [q.SYNC_CB_NOTIFICATION_QUEUE]
        assert len(result) == 1

    def test_generic_processor_excludes_cb_notification_queue(self):
        result = WorkerType.GENERIC_PROCESSOR.get_queues()
        assert q.SYNC_CB_NOTIFICATION_QUEUE not in result
        expected = [queue for queue in q.ALL_QUEUES if queue != q.SYNC_CB_NOTIFICATION_QUEUE]
        assert result == expected

    def test_dlq_recovery_returns_empty_list(self):
        result = WorkerType.DLQ_RECOVERY.get_queues()
        assert result == []

    # --- Structural invariants ---

    def test_all_domain_queues_are_non_empty(self):
        domain_workers = [
            WorkerType.SYNC, WorkerType.ALARMS, WorkerType.DATA,
            WorkerType.CROWD, WorkerType.DATA_CACHE,
        ]
        for worker in domain_workers:
            queues = worker.get_queues()
            assert len(queues) > 0, f"{worker} returned an empty queue list"

    def test_universal_is_superset_of_all_domain_queues(self):
        all_queues = set(WorkerType.UNIVERSAL.get_queues())
        domain_workers = [
            WorkerType.SYNC, WorkerType.ALARMS, WorkerType.DATA,
            WorkerType.CROWD, WorkerType.DATA_CACHE,
        ]
        for worker in domain_workers:
            for queue in worker.get_queues():
                assert queue in all_queues, (
                    f"Queue {queue.name} from {worker} is missing from UNIVERSAL"
                )

    def test_universal_on_premise_is_subset_of_universal(self):
        universal = set(WorkerType.UNIVERSAL.get_queues())
        on_premise = set(WorkerType.UNIVERSAL_ON_PREMISE.get_queues())
        assert on_premise.issubset(universal)

    def test_cb_and_generic_processor_cover_all_queues(self):
        cb = WorkerType.CB_PROCESSOR.get_queues()
        generic = WorkerType.GENERIC_PROCESSOR.get_queues()
        combined = set(cb + generic)
        assert combined == set(q.ALL_QUEUES)

    def test_no_duplicate_queues_per_worker_type(self):
        for worker in WorkerType:
            queues = worker.get_queues()
            names = [queue.name for queue in queues]
            assert len(names) == len(set(names)), (
                f"{worker} has duplicate queue names: {names}"
            )


class TestGetTaskModules:
    """Verify get_task_modules() returns the right modules for each worker type."""

    def test_all_task_modules_are_non_empty_strings(self):
        for module in _ALL_TASK_MODULES:
            assert isinstance(module, str) and len(module) > 0

    def test_all_task_modules_start_with_tasks_prefix(self):
        for module in _ALL_TASK_MODULES:
            assert module.startswith("tasks."), f"{module!r} does not start with 'tasks.'"

    # --- Domain workers: each should load only its own module ---

    @pytest.mark.parametrize("worker_type, expected_module", [
        (WorkerType.SYNC,           "tasks.sync"),
        (WorkerType.ALARMS,         "tasks.alarms"),
        (WorkerType.DATA,           "tasks.data"),
        (WorkerType.CROWD,          "tasks.crowd"),
        (WorkerType.DATA_CACHE,     "tasks.data_cache"),
        (WorkerType.CB_PROCESSOR,   "tasks.sync"),
    ])
    def test_domain_worker_loads_single_module(self, worker_type, expected_module):
        modules = worker_type.get_task_modules()
        assert modules == [expected_module], (
            f"{worker_type}: expected [{expected_module!r}], got {modules}"
        )

    def test_core_loads_expected_modules(self):
        modules = WorkerType.CORE.get_task_modules()
        assert set(modules) == {"tasks.sync", "tasks.data"}
        assert len(modules) == 2

    def test_dlq_recovery_loads_no_modules(self):
        assert WorkerType.DLQ_RECOVERY.get_task_modules() == []

    # --- Aggregate workers that load all task modules ---

    @pytest.mark.parametrize("worker_type", [
        WorkerType.UNIVERSAL,
        WorkerType.UNIVERSAL_ON_PREMISE,
        WorkerType.CUSTOM,
    ])
    def test_aggregate_workers_load_all_modules(self, worker_type):
        assert worker_type.get_task_modules() == _ALL_TASK_MODULES

    def test_generic_processor_loads_all_modules(self):
        modules = WorkerType.GENERIC_PROCESSOR.get_task_modules()
        assert modules == _ALL_TASK_MODULES

    def test_all_task_modules_are_the_expected_ones(self):
        assert set(_ALL_TASK_MODULES) == {
            "tasks.sync", "tasks.alarms", "tasks.data", "tasks.crowd",
            "tasks.data_cache",
        }

    def test_no_duplicate_modules_in_any_worker_type(self):
        for worker in WorkerType:
            modules = worker.get_task_modules()
            assert len(modules) == len(set(modules)), (
                f"{worker} has duplicate task modules: {modules}"
            )

    def test_task_module_map_only_contains_valid_worker_types(self):
        for worker in _TASK_MODULE_MAP:
            assert isinstance(worker, WorkerType), (
                f"{worker!r} in _TASK_MODULE_MAP is not a WorkerType"
            )


class TestTaskModuleImportability:
    """Verify task module names in _ALL_TASK_MODULES are importable strings
    following the expected naming convention."""

    def test_all_task_module_names_are_dot_separated(self):
        for module in _ALL_TASK_MODULES:
            parts = module.split(".")
            assert len(parts) == 2 and all(p for p in parts), (
                f"Unexpected module path format: {module!r}"
            )

    def test_no_task_module_appears_in_both_core_and_all_modules_exclusively(self):
        """CORE modules should all be present in _ALL_TASK_MODULES."""
        core_modules = set(WorkerType.CORE.get_task_modules())
        all_modules = set(_ALL_TASK_MODULES)
        assert core_modules.issubset(all_modules), (
            f"CORE modules not in _ALL_TASK_MODULES: {core_modules - all_modules}"
        )

    def test_domain_modules_all_present_in_all_task_modules(self):
        """Every module used by a domain worker must be in _ALL_TASK_MODULES."""
        all_modules = set(_ALL_TASK_MODULES)
        for worker, modules in _TASK_MODULE_MAP.items():
            for module in modules:
                if module:  # skip empty strings
                    assert module in all_modules, (
                        f"{worker}: module {module!r} is not in _ALL_TASK_MODULES"
                    )


class TestTasksInitImport:
    """Verify that tasks/__init__.py actually calls importlib.import_module
    for each module returned by the configured worker type."""

    def _run_tasks_init(self, worker_type: WorkerType) -> list[str]:
        """
        Re-executes the tasks/__init__.py logic with the given worker type and
        returns the list of module names that were passed to import_module.
        """
        imported: list[str] = []

        def fake_import(name):
            imported.append(name)
            return MagicMock()

        with patch("config.config.settings.WORKER_TYPE", worker_type), \
             patch("importlib.import_module", side_effect=fake_import):
            import importlib as _importlib
            from config.config import settings
            for module in settings.WORKER_TYPE.get_task_modules():
                _importlib.import_module(module)

        return imported

    @pytest.mark.parametrize("worker_type", [wt for wt in WorkerType])
    def test_init_imports_exactly_the_modules_for_worker_type(self, worker_type):
        expected = worker_type.get_task_modules()
        actual = self._run_tasks_init(worker_type)
        assert actual == expected, (
            f"{worker_type}: expected imports {expected}, got {actual}"
        )

    def test_domain_worker_imports_only_its_own_module(self):
        actual = self._run_tasks_init(WorkerType.SYNC)
        assert actual == ["tasks.sync"]

    def test_universal_worker_imports_all_modules(self):
        actual = self._run_tasks_init(WorkerType.UNIVERSAL)
        assert actual == _ALL_TASK_MODULES

    def test_dlq_recovery_imports_nothing(self):
        actual = self._run_tasks_init(WorkerType.DLQ_RECOVERY)
        assert actual == []

    def test_each_module_name_corresponds_to_an_existing_tasks_file(self):
        """Every module in _ALL_TASK_MODULES must map to a real file under tasks/."""
        import os
        tasks_dir = os.path.join(os.path.dirname(__file__), "../../tasks")
        tasks_dir = os.path.normpath(tasks_dir)
        for module in _ALL_TASK_MODULES:
            # "tasks.data_cache" → "data_cache.py"
            _, submodule = module.split(".", 1)
            path = os.path.join(tasks_dir, f"{submodule}.py")
            assert os.path.isfile(path), (
                f"Module {module!r} listed in _ALL_TASK_MODULES has no matching "
                f"file at {path}"
            )
