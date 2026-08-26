"""
Verification report machinery.

Every test is a named "check" (via the @pytest.mark.check marker). This module
collects each check's outcome and renders a final human-readable report that
says what was verified, what failed, and how to fix it.

Failures raised as CheckFailure carry remediation advice that is printed in the
report. Checks can declare dependencies on earlier checks with require(); when
a dependency did not pass, the check is skipped as "blocked" instead of failing
with a confusing secondary error.
"""

import os
import shutil
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pytest


class CheckFailure(AssertionError):
    """A check failure that carries remediation advice for the report."""

    def __init__(self, message: str, advice: Optional[List[str]] = None):
        super().__init__(message)
        self.advice = advice or []


def fail(message: str, *advice: str) -> None:
    """Fail the current check with remediation advice."""
    raise CheckFailure(message, list(advice))


@dataclass
class CheckResult:
    """Recorded outcome of one check."""

    check_id: str
    title: str
    section: str
    outcome: str  # "passed" | "failed" | "skipped"
    message: str = ""
    advice: List[str] = field(default_factory=list)


# Ordered results, recorded as tests run. Keyed lookups for dependencies.
RESULTS: List[CheckResult] = []
RESULTS_BY_ID: Dict[str, CheckResult] = {}

# Extra remarks (warnings that are not failures) to print in the report.
NOTES: List[str] = []


def record(result: CheckResult) -> None:
    RESULTS.append(result)
    RESULTS_BY_ID[result.check_id] = result


def note(message: str) -> None:
    """Add a non-failure remark to the final report."""
    NOTES.append(message)


def passed(check_id: str) -> bool:
    result = RESULTS_BY_ID.get(check_id)
    return result is not None and result.outcome == "passed"


def require(*check_ids: str) -> None:
    """Skip the current check when a dependency did not pass."""
    for check_id in check_ids:
        result = RESULTS_BY_ID.get(check_id)
        if result is None:
            pytest.skip(f"blocked: prerequisite check '{check_id}' did not run")
        if result.outcome != "passed":
            pytest.skip(f"blocked: prerequisite '{result.title}' {result.outcome}")


# --- terminal rendering ------------------------------------------------------

_USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _color(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def _green(text: str) -> str:
    return _color("32", text)


def _red(text: str) -> str:
    return _color("31", text)


def _yellow(text: str) -> str:
    return _color("33", text)


def _bold(text: str) -> str:
    return _color("1", text)


_SYMBOLS = {"passed": "✓", "failed": "✗", "skipped": "—"}
_PAINTERS = {"passed": _green, "failed": _red, "skipped": _yellow}


def render_report(write=print) -> None:
    """Print the final verification report."""
    width = min(shutil.get_terminal_size().columns, 100)

    write("")
    write(_bold("=" * width))
    write(_bold("  PID Gijón — platform verification report"))
    write(_bold("=" * width))

    current_section = None
    for result in RESULTS:
        if result.section != current_section:
            current_section = result.section
            write("")
            write(_bold(f"  {current_section}"))
        painter = _PAINTERS[result.outcome]
        symbol = painter(_SYMBOLS[result.outcome])
        write(f"   {symbol} {result.title}")
        if result.outcome == "skipped" and result.message:
            write(_yellow(f"       ({result.message})"))
        if result.outcome == "failed":
            if result.message:
                for line in result.message.splitlines():
                    write(_red(f"       {line}"))
            for advice_line in result.advice:
                first = True
                for line in advice_line.splitlines():
                    prefix = "       ↳ " if first else "         "
                    write(f"{prefix}{line}")
                    first = False

    if NOTES:
        write("")
        write(_bold("  Notes"))
        for message in NOTES:
            write(_yellow(f"   • {message}"))

    counts = {"passed": 0, "failed": 0, "skipped": 0}
    for result in RESULTS:
        counts[result.outcome] += 1

    write("")
    write(_bold("-" * width))
    summary = (
        f"  {_green(str(counts['passed']) + ' passed')}, "
        f"{_red(str(counts['failed']) + ' failed')}, "
        f"{_yellow(str(counts['skipped']) + ' skipped/blocked')}"
    )
    write(summary)
    if counts["failed"]:
        write("")
        write(
            "  Failures cascade: checks run in dependency order, so fix the FIRST\n"
            "  failing check above, then re-run the suite."
        )
    elif counts["skipped"] and not counts["failed"]:
        write("")
        write("  No failures, but some checks were skipped — see reasons above.")
    else:
        write("")
        write(_green("  All checks passed — the platform looks healthy. 🎉"))
    write(_bold("=" * width))
    write("")
