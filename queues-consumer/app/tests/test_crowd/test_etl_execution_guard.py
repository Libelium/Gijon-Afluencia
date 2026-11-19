"""
run_etl_once: an ETL window must end up executed successfully exactly once.

The execution row used to be created *before*
running and never updated, and any later dispatch of the same window was
skipped because the row existed. A job that failed or was killed therefore
left a permanent hole in visits / uniqueVisitors.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from config.config import settings
from models.crud.crud_etl_executions import (
    ETL_STATUS_FAILED,
    ETL_STATUS_STARTED,
    ETL_STATUS_SUCCESS,
    execution_is_running,
    execution_is_successful,
)
from jobs.crowd.all_crowd_process_vistors_jobs import ProcessVisitorsAll
from schemas.crowd_process_visitors_request_schema import (
    AllProcessVisitorsRequest,
    ProcessVisitorsEntity,
    ProcessVisitorsRequest,
)
from tasks import crowd as crowd_tasks

ETL_TYPE = "platform.crowd.process_visitors"


class _Retry(Exception):
    """Stands in for celery.exceptions.Retry raised by Task.retry()."""


def _execution(status, age_minutes=0, **extra):
    moment = datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
    return SimpleNamespace(
        id=1, status=status, created_at=moment, updated_at=moment, error=None, **extra
    )


def _request(force=False):
    return ProcessVisitorsRequest(
        user_id=119,
        entities=[
            ProcessVisitorsEntity(
                id=1, urn="urn:ngsi-ld:CrowdFlowEvent:x_CFE", tenant="t", scope="/"
            )
        ],
        start_date="2026-05-01T05:00:00",
        end_date="2026-05-01T06:00:00",
        mode="tourism",
        aggregation_mode="none",
        force=force,
    )


@pytest.fixture
def task():
    t = MagicMock()
    t.request.retries = 0
    t.retry.side_effect = _Retry()
    return t


@pytest.fixture
def crud():
    with (
        patch.object(crowd_tasks, "find_etl_execution") as find,
        patch.object(crowd_tasks, "create_etl_execution") as create,
        patch.object(crowd_tasks, "mark_etl_execution") as mark,
    ):
        create.return_value = _execution(ETL_STATUS_STARTED)
        yield SimpleNamespace(find=find, create=create, mark=mark)


def _run(task, crud, previous, etl=None, force=False, db=None):
    crud.find.return_value = previous
    if etl is None:
        etl = MagicMock()
        etl.execute_once.return_value = 0
    ran = crowd_tasks.run_etl_once(
        task, db or MagicMock(), ETL_TYPE, _request(force), lambda: etl
    )
    return ran, etl


# --- status predicates ------------------------------------------------------


def test_legacy_row_without_status_counts_as_success():
    assert execution_is_successful(_execution(None))
    assert execution_is_successful(_execution(ETL_STATUS_SUCCESS))
    assert not execution_is_successful(_execution(ETL_STATUS_FAILED))
    assert not execution_is_successful(_execution(ETL_STATUS_STARTED))
    assert not execution_is_successful(None)


def test_started_is_running_only_while_fresh():
    assert execution_is_running(_execution(ETL_STATUS_STARTED, age_minutes=5))
    stale = settings.CROWD_ETL_STALE_RUNNING_MINUTES + 1
    assert not execution_is_running(_execution(ETL_STATUS_STARTED, age_minutes=stale))
    assert not execution_is_running(_execution(ETL_STATUS_FAILED))


def test_running_check_accepts_naive_timestamps():
    naive = _execution(ETL_STATUS_STARTED)
    naive.updated_at = datetime.utcnow()
    assert execution_is_running(naive)


# --- run_etl_once -----------------------------------------------------------


def test_first_run_creates_row_runs_and_marks_success(task, crud):
    ran, etl = _run(task, crud, previous=None)

    assert ran is True
    etl.execute_once.assert_called_once()
    crud.create.assert_called_once()
    assert crud.create.call_args.kwargs["user_id"] == 119
    crud.mark.assert_called_once()
    assert crud.mark.call_args.args[2] == ETL_STATUS_SUCCESS


def test_successful_window_is_skipped(task, crud):
    ran, etl = _run(task, crud, previous=_execution(ETL_STATUS_SUCCESS))

    assert ran is False
    etl.execute_once.assert_not_called()
    crud.create.assert_not_called()
    crud.mark.assert_not_called()


def test_legacy_window_is_skipped(task, crud):
    ran, etl = _run(task, crud, previous=_execution(None))

    assert ran is False
    etl.execute_once.assert_not_called()


def test_failed_window_is_rerun_without_new_row(task, crud):
    previous = _execution(ETL_STATUS_FAILED)
    ran, etl = _run(task, crud, previous=previous)

    assert ran is True
    etl.execute_once.assert_called_once()
    crud.create.assert_not_called()
    statuses = [c.args[2] for c in crud.mark.call_args_list]
    assert statuses == [ETL_STATUS_STARTED, ETL_STATUS_SUCCESS]
    assert all(c.args[1] is previous for c in crud.mark.call_args_list)


def test_fresh_started_window_is_not_run_twice(task, crud):
    ran, etl = _run(task, crud, previous=_execution(ETL_STATUS_STARTED, age_minutes=1))

    assert ran is False
    etl.execute_once.assert_not_called()


def test_stale_started_window_is_rerun(task, crud):
    stale = settings.CROWD_ETL_STALE_RUNNING_MINUTES + 10
    ran, etl = _run(
        task, crud, previous=_execution(ETL_STATUS_STARTED, age_minutes=stale)
    )

    assert ran is True
    etl.execute_once.assert_called_once()


def test_force_reruns_a_successful_window(task, crud):
    ran, etl = _run(task, crud, previous=_execution(ETL_STATUS_SUCCESS), force=True)

    assert ran is True
    etl.execute_once.assert_called_once()
    statuses = [c.args[2] for c in crud.mark.call_args_list]
    assert statuses == [ETL_STATUS_STARTED, ETL_STATUS_SUCCESS]


def test_failure_without_retries_marks_failed_and_reraises(task, crud):
    """Default: no in-task retry; the lookback re-dispatch picks the window up later."""
    etl = MagicMock()
    etl.execute_once.side_effect = RuntimeError("timescale down")

    with pytest.raises(RuntimeError, match="timescale down"):
        _run(task, crud, previous=None, etl=etl)

    failed = [c for c in crud.mark.call_args_list if c.args[2] == ETL_STATUS_FAILED]
    assert len(failed) == 1
    assert failed[0].kwargs["error"] == "timescale down"
    task.retry.assert_not_called()


def test_failure_marks_failed_with_error_and_retries(task, crud):
    etl = MagicMock()
    etl.execute_once.side_effect = RuntimeError("timescale down")

    with patch.object(crowd_tasks.settings, "CROWD_ETL_MAX_RETRIES", 2), pytest.raises(
        _Retry
    ):
        _run(task, crud, previous=None, etl=etl)

    failed = [c for c in crud.mark.call_args_list if c.args[2] == ETL_STATUS_FAILED]
    assert len(failed) == 1
    assert failed[0].kwargs["error"] == "timescale down"
    task.retry.assert_called_once()
    assert task.retry.call_args.kwargs["max_retries"] == 2
    assert (
        task.retry.call_args.kwargs["countdown"]
        >= settings.CROWD_ETL_RETRY_BACKOFF_SECONDS
    )


def test_failure_after_last_retry_reraises_original_error(task, crud):
    task.request.retries = 2
    etl = MagicMock()
    etl.execute_once.side_effect = RuntimeError("still down")

    with patch.object(crowd_tasks.settings, "CROWD_ETL_MAX_RETRIES", 2), pytest.raises(
        RuntimeError, match="still down"
    ):
        _run(task, crud, previous=None, etl=etl)

    task.retry.assert_not_called()
    assert crud.mark.call_args.args[2] == ETL_STATUS_FAILED


def test_no_result_marks_failed_without_raising(task, crud):
    etl = MagicMock()
    etl.execute_once.return_value = -1

    ran, _ = _run(task, crud, previous=None, etl=etl)

    assert ran is True
    statuses = [c.args[2] for c in crud.mark.call_args_list]
    assert statuses == [ETL_STATUS_FAILED]
    assert crud.mark.call_args.kwargs["error"] == "execute_once returned -1"
    task.retry.assert_not_called()


def test_failure_rolls_back_session_before_marking_failed(task, crud):
    db = MagicMock()
    calls = MagicMock()
    db.rollback.side_effect = lambda: calls.rollback()
    crud.mark.side_effect = lambda *a, **k: calls.mark(a[2])
    etl = MagicMock()
    etl.execute_once.side_effect = RuntimeError("InFailedSqlTransaction")

    with pytest.raises(RuntimeError):
        _run(task, crud, previous=None, etl=etl, db=db)

    assert [c[0] for c in calls.mock_calls] == ["rollback", "mark"]
    assert calls.mark.call_args.args[0] == ETL_STATUS_FAILED


@pytest.mark.parametrize("previous", [None, _execution(ETL_STATUS_FAILED)])
def test_connection_is_released_before_running_the_etl(task, crud, previous):
    db = MagicMock()
    calls = MagicMock()
    db.commit.side_effect = lambda: calls.commit()
    etl = MagicMock()

    def execute_once():
        calls.execute_once()
        return 0

    etl.execute_once.side_effect = execute_once

    _run(task, crud, previous=previous, etl=etl, db=db)

    assert [c[0] for c in calls.mock_calls] == ["commit", "execute_once"]


def test_no_open_transaction_while_the_etl_runs(task, crud):
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    engine = create_engine("sqlite://")
    db = Session(engine)
    crud.create.side_effect = lambda *a, **k: (
        db.execute(text("SELECT 1")),
        _execution(ETL_STATUS_STARTED),
    )[1]
    seen = {}

    def execute_once():
        seen["in_transaction"] = db.in_transaction()
        return 0

    etl = MagicMock()
    etl.execute_once.side_effect = execute_once

    _run(task, crud, previous=None, etl=etl, db=db)

    assert seen["in_transaction"] is False
    db.close()
    engine.dispose()


def test_retry_countdown_backs_off_and_caps():
    first = crowd_tasks.etl_retry_countdown(0)
    second = crowd_tasks.etl_retry_countdown(1)
    huge = crowd_tasks.etl_retry_countdown(20)
    base = settings.CROWD_ETL_RETRY_BACKOFF_SECONDS
    cap = settings.CROWD_ETL_RETRY_BACKOFF_MAX_SECONDS

    assert base <= first <= base * 1.1
    assert 2 * base <= second <= 2 * base * 1.1
    assert cap <= huge <= cap * 1.1


# --- dispatcher look-back ---------------------------------------------------


def test_hourly_dispatcher_covers_the_lookback_window():
    """
    With no explicit dates the dispatcher must enqueue the last
    CROWD_ETL_LOOKBACK_HOURS windows, not only the previous hour, so a window
    that failed or was never dispatched gets another chance on the next tick.
    """
    entities = [
        ProcessVisitorsEntity(
            id=1, urn="urn:ngsi-ld:CrowdFlowEvent:x_CFE", tenant="t", scope="/"
        )
    ]
    job = ProcessVisitorsAll(
        request=AllProcessVisitorsRequest(start_date=None, end_date=None),
        db=MagicMock(),
    )

    with patch("tasks.crowd.process_visitors_job.delay") as delay:
        job._ProcessVisitorsAll__start_jobs(user_id=119, entities=entities)

    assert delay.call_count == settings.CROWD_ETL_LOOKBACK_HOURS
    starts = [
        (
            datetime.fromisoformat(c.args[0].start_date)
            if isinstance(c.args[0].start_date, str)
            else c.args[0].start_date
        )
        for c in delay.call_args_list
    ]
    assert all(s.minute == 0 and s.second == 0 for s in starts)
    assert starts == sorted(starts)
    assert starts[-1] + timedelta(hours=1) == datetime.now().replace(
        minute=0, second=0, microsecond=0
    )


def test_window_killed_mid_run_is_rerun_within_the_lookback():
    """A window lost at its first tick must be stale at the next one, still inside the lookback."""
    tick_minutes = settings.CROWD_PROCESS_VISITORS_INTERVAL // 60
    killed = _execution(ETL_STATUS_STARTED, age_minutes=tick_minutes)

    assert settings.CROWD_ETL_LOOKBACK_HOURS * 60 > tick_minutes
    assert not execution_is_running(killed)
    assert execution_is_running(
        _execution(ETL_STATUS_STARTED, age_minutes=settings.CROWD_ETL_STALE_RUNNING_MINUTES - 1)
    )
