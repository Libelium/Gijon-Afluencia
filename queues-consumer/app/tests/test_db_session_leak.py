"""
Regression test for the default-arg session capture antipattern.

The previous pattern was:

    def __init__(self, ..., db: Session = next(deps.get_db())):

`next(deps.get_db())` is evaluated **once at module import time** (per Celery
fork). It captures a SQLAlchemy `Session` object and never releases it. The
generator's `finally: db.close()` only runs on a *second* `next()` call, which
never happens — so the moment the captured session executes its first query,
its connection is checked out from the pool and stays held for the worker's
lifetime. Combined with `pool_size=1, max_overflow=0`, this deadlocks any
other code that needs a connection.

A pure runtime check on `engine.pool.checkedout()` after import does NOT
detect this — `scoped_session` is lazy and only acquires a connection on
first query. So we use AST-level detection: walk every `.py` file in the
job tree and fail if any function definition has a default argument that
evaluates a database-session generator.

The fix is to use the context managers in `db.session_helpers` instead.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator

import pytest


# Generator factories that return a SQLAlchemy Session. Calling `next()` on
# any of these inside a default argument is the antipattern.
SESSION_GENERATORS: set[str] = {
    "get_db",
    "get_db_realtime",
    "get_session",
}

# Trees we audit. Each entry is a path relative to the app/ directory.
AUDITED_TREES: tuple[str, ...] = (
    "jobs",
    "models/crud",
    "helpers",
    "utils",
)

APP_ROOT = Path(__file__).resolve().parent.parent


def _python_files(root: Path) -> Iterator[Path]:
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _is_session_generator_call(default: ast.AST) -> bool:
    """
    Returns True if `default` is a call like `next(deps.get_db())`,
    `next(realtime.get_db_realtime())`, or any other `next(<x>.<gen>())`
    where `<gen>` is one of the known session generators.
    """
    if not isinstance(default, ast.Call):
        return False
    if not (isinstance(default.func, ast.Name) and default.func.id == "next"):
        return False
    if not default.args:
        return False
    inner = default.args[0]
    if not isinstance(inner, ast.Call):
        return False
    inner_func = inner.func
    if isinstance(inner_func, ast.Attribute):
        return inner_func.attr in SESSION_GENERATORS
    if isinstance(inner_func, ast.Name):
        return inner_func.id in SESSION_GENERATORS
    return False


def _bad_defaults(tree: ast.AST) -> list[tuple[int, str]]:
    """
    Walk the AST and return a list of (lineno, function_name) tuples where a
    function definition uses a session-generator call as a default argument.
    Both positional and keyword-only defaults are checked.
    """
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        defaults = list(node.args.defaults) + list(node.args.kw_defaults)
        for default in defaults:
            if default is not None and _is_session_generator_call(default):
                findings.append((node.lineno, node.name))
                break
    return findings


@pytest.mark.parametrize("tree", AUDITED_TREES)
def test_no_session_generator_in_default_args(tree: str) -> None:
    """
    No function in `app/<tree>/**/*.py` should use a session-generator as a
    default argument. This is the antipattern that previously deadlocked the
    pool — see this module's docstring for context.

    If this test fails, replace the offending default with `Optional[Session]
    = None` and acquire/release the session inside the function body using
    the helpers in `app/db/session_helpers.py`.
    """
    target_root = APP_ROOT / tree
    if not target_root.exists():
        pytest.skip(f"{target_root} does not exist")

    offenders: list[str] = []
    for path in _python_files(target_root):
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        try:
            module_ast = ast.parse(source, filename=str(path))
        except SyntaxError:
            # Don't mask other syntax errors — let pytest's collection step
            # surface them. Here we just skip parsing failures because that's
            # not what this test is about.
            continue
        for lineno, func_name in _bad_defaults(module_ast):
            offenders.append(
                f"{path.relative_to(APP_ROOT)}:{lineno} — {func_name}() "
                "uses a session generator as a default argument"
            )

    assert not offenders, (
        "Found default-arg session capture antipattern. "
        "Use db.session_helpers.main_session() / realtime_session() inside "
        "the function body instead.\n  - " + "\n  - ".join(offenders)
    )
