"""
Context managers for SQLAlchemy sessions used by Celery jobs.

These exist because the previous pattern — passing a default-arg session via
`def __init__(self, ..., db: Session = next(deps.get_db()))` — captures a
single session at module import time. The captured session never closes (the
underlying generator's `finally` only runs on a second `next()` call), so the
connection it holds stays checked out forever. Combined with `pool_size=1`
and `max_overflow=0`, that one held connection deadlocks any other code that
needs to acquire one (e.g. `Error: QueuePool limit of size 1 overflow 0
reached, connection timed out`).

The helpers below are the canonical replacement: jobs accept an optional
injected session (for tests or rare cases where the caller already manages
its own), and otherwise open + close a fresh session per `handle()` call.
"""
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy.orm import Session

from db.session import SessionLocal
from db.realtime import RealtimeSessionLocal


@contextmanager
def main_session(injected: Optional[Session] = None) -> Iterator[Session]:
    """
    Yield a platform DB session.

    If `injected` is provided, yield it as-is — the caller owns its lifecycle
    and we will not close it. Otherwise open a fresh `SessionLocal()` and
    close it on exit, returning the connection to the pool.
    """
    if injected is not None:
        yield injected
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def realtime_session(injected: Optional[Session] = None) -> Iterator[Session]:
    """Same shape as `main_session()` but bound to the realtime DB engine."""
    if injected is not None:
        yield injected
        return

    db = RealtimeSessionLocal()
    try:
        yield db
    finally:
        db.close()
