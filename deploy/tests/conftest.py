"""
Pytest wiring for the platform verification suite.

Every test carries a @pytest.mark.check(id=..., title=..., section=...) marker.
This plugin records each check's outcome (including remediation advice from
CheckFailure) and prints the final verification report after the run.
"""

from typing import List, Tuple

import pytest

from helpers import report
from helpers.report import CheckFailure, CheckResult


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "check(id, title, section): describe a verification check for the report",
    )
    config.addinivalue_line(
        "markers", "kubernetes: checks that need kubectl access to the cluster"
    )
    config.addinivalue_line(
        "markers", "api: checks that exercise the platform through its public API"
    )


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items):
    """Force checks to run in stage order (test_00 → test_06).

    The stages are a pipeline that shares state through helpers.session (login →
    device → data) and gate each other with require(). They must run in file
    order; this re-imposes it even if a shuffling plugin (e.g. pytest-randomly)
    is installed. trylast=True runs this after any such plugin. The sort is
    stable, so definition order within a file is preserved.
    """
    items.sort(key=lambda item: item.location[0])


def _failure_details(excinfo) -> Tuple[str, List[str]]:
    if excinfo is None:
        return "", []
    exc = excinfo.value
    if isinstance(exc, CheckFailure):
        return str(exc), list(exc.advice)
    if isinstance(exc, AssertionError):
        message = str(exc).splitlines()[0] if str(exc) else "assertion failed"
        return message, []
    return f"unexpected error: {exc!r}", [
        "This is likely a bug in the test suite or an unreachable endpoint; "
        "re-run with -v --tb=short for the full traceback."
    ]


def _skip_reason(rep) -> str:
    if isinstance(rep.longrepr, tuple):
        return rep.longrepr[2].replace("Skipped: ", "")
    return str(rep.longrepr or "")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()

    marker = item.get_closest_marker("check")
    if marker is None:
        return

    check_id = marker.kwargs.get("id", item.nodeid)
    title = marker.kwargs.get("title", item.name)
    section = marker.kwargs.get("section", "Other")

    # Setup-phase skips/errors (e.g. a fixture failed) must be recorded too;
    # otherwise only record the call phase.
    if rep.when == "setup" and rep.outcome == "passed":
        return
    if rep.when == "teardown":
        return
    if check_id in report.RESULTS_BY_ID and report.RESULTS_BY_ID[check_id].outcome != "passed":
        return  # keep the first (most meaningful) outcome

    if rep.skipped:
        result = CheckResult(check_id, title, section, "skipped", _skip_reason(rep))
    elif rep.failed:
        message, advice = _failure_details(call.excinfo)
        result = CheckResult(check_id, title, section, "failed", message, advice)
    else:
        result = CheckResult(check_id, title, section, "passed")

    report.record(result)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    writer = terminalreporter._tw

    def write(line: str = ""):
        writer.line(line)

    report.render_report(write)
