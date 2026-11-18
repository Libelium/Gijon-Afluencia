"""
Tests for the celery beat scheduler DB engine options.

DatabaseScheduler queries the DB on every tick (schedule_changed) without
catching errors, so a stale pooled connection kills beat silently. The engine
must pre-ping and recycle its connections.
"""

from unittest.mock import patch

import pytest
from sqlalchemy_celery_beat import schedulers

from config.celery import app as celery_app
from config.config import settings

EXPECTED_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": settings.CELERY_BEAT_DB_POOL_RECYCLE_SECONDS,
}


class _StopInit(Exception):
    """Aborts DatabaseScheduler.__init__ once the engine options are captured."""


class TestBeatEngineOptions:
    def test_beat_uses_database_scheduler(self):
        assert (
            celery_app.conf.beat_scheduler
            == "sqlalchemy_celery_beat.schedulers:DatabaseScheduler"
        )

    def test_engine_pre_pings_and_recycles_connections(self):
        assert celery_app.conf.beat_engine_options == EXPECTED_ENGINE_OPTIONS

    def test_database_scheduler_forwards_options_to_the_engine(self):
        with patch.object(
            schedulers.session_manager, "create_session", side_effect=_StopInit
        ) as create_session:
            with pytest.raises(_StopInit):
                schedulers.DatabaseScheduler(app=celery_app)

        _, kwargs = create_session.call_args
        assert {k: kwargs[k] for k in EXPECTED_ENGINE_OPTIONS} == EXPECTED_ENGINE_OPTIONS
