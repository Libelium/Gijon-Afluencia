"""
Regression tests for the queues-consumer security findings:
SEC-016, SEC-017, SEC-018, SEC-020, SEC-043 and SEC-045.

These endpoints and the timeseries schema bootstrap had no test coverage at all,
which is how an unauthenticated task dispatcher, an unauthenticated SSRF, a path
traversal and a SQL-injectable CREATE SCHEMA all shipped together.
"""

import os
import re
import uuid

import pytest
from fastapi import HTTPException

import api
from jobs.timeseries.timescale.sql_template_loader import (InvalidSchemaName,
                                                           quote_identifier,
                                                           render_check_schema,
                                                           validate_schema_name)
from utils.queue import Queue


# --------------------------------------------------------------------------- #
# SEC-043 - CORS
# --------------------------------------------------------------------------- #
class TestCors:
    def test_no_wildcard_origin_is_ever_registered(self):
        """
        `allow_origins=["*"]` with `allow_credentials=True` is the combination
        the CORS spec forbids: Starlette reflects the caller's own Origin back
        with Access-Control-Allow-Credentials.
        """
        for middleware in api.application.user_middleware:
            origins = middleware.kwargs.get("allow_origins", ())
            assert "*" not in origins

    def test_credentials_are_only_allowed_with_an_explicit_origin_list(self):
        for middleware in api.application.user_middleware:
            if middleware.kwargs.get("allow_credentials"):
                assert middleware.kwargs.get("allow_origins")


# --------------------------------------------------------------------------- #
# SEC-016 - the unauthenticated SSRF
# --------------------------------------------------------------------------- #
class TestTestConnectionIsGone:
    def test_the_endpoint_is_not_registered(self):
        paths = {r.path for r in api.application.routes if hasattr(r, "path")}
        assert "/test-connection" not in paths

    def test_no_handler_is_left_behind(self):
        assert not hasattr(api, "test_connection")


# --------------------------------------------------------------------------- #
# SEC-017 / SEC-018 - shared-secret authentication
# --------------------------------------------------------------------------- #
class TestApiToken:
    def test_unconfigured_token_refuses_rather_than_allows(self, monkeypatch):
        """Fail-closed. An unset secret must not mean "serve it openly"."""
        monkeypatch.setattr(api.settings, "QUEUES_CONSUMER_API_TOKEN", "")
        with pytest.raises(HTTPException) as excinfo:
            api.require_api_token("anything")
        assert excinfo.value.status_code == 503

    def test_wrong_token_is_rejected(self, monkeypatch):
        monkeypatch.setattr(api.settings, "QUEUES_CONSUMER_API_TOKEN", "s3cret")
        with pytest.raises(HTTPException) as excinfo:
            api.require_api_token("nope")
        assert excinfo.value.status_code == 401

    def test_missing_token_is_rejected(self, monkeypatch):
        monkeypatch.setattr(api.settings, "QUEUES_CONSUMER_API_TOKEN", "s3cret")
        with pytest.raises(HTTPException) as excinfo:
            api.require_api_token("")
        assert excinfo.value.status_code == 401

    def test_correct_token_passes(self, monkeypatch):
        monkeypatch.setattr(api.settings, "QUEUES_CONSUMER_API_TOKEN", "s3cret")
        assert api.require_api_token("s3cret") is None

    @pytest.mark.parametrize("path", ["/publish", "/stream/{pipeline_id}/{entity_id}/{file}"])
    def test_the_protected_routes_declare_the_dependency(self, path):
        route = next(r for r in api.application.routes
                     if getattr(r, "path", None) == path)
        # route.dependencies holds Depends objects; the callable is `.dependency`.
        assert any(d.dependency is api.require_api_token for d in route.dependencies)


# --------------------------------------------------------------------------- #
# SEC-017 - task allow list
# --------------------------------------------------------------------------- #
class TestPublishAllowList:
    def test_celery_builtins_are_not_publishable(self):
        """
        `celery_app.tasks[name]` resolves Celery's own built-ins too, so an
        unrestricted /publish let the caller pick which of them ran.
        """
        for builtin in ("celery.backend_cleanup", "celery.chord", "celery.group",
                        "celery.chain", "celery.map"):
            assert builtin not in api._publishable_tasks()

    def test_the_default_list_is_what_the_platform_actually_publishes(self):
        assert api._publishable_tasks() == api.PUBLISHABLE_TASKS_DEFAULT

    def test_the_list_can_be_narrowed_by_configuration(self, monkeypatch):
        monkeypatch.setattr(api.settings, "PUBLISHABLE_TASKS",
                            "platform.data.importation_job")
        assert api._publishable_tasks() == frozenset({"platform.data.importation_job"})


# --------------------------------------------------------------------------- #
# SEC-018 - path traversal in the HLS route
# --------------------------------------------------------------------------- #
class TestHlsFileName:
    @pytest.mark.parametrize("name", [
        "index.m3u8", "segment_0.ts", "chunk-12.m4s", "clip.mp4", "subs.vtt",
    ])
    def test_real_hls_names_are_accepted(self, name):
        assert api._HLS_FILE_RE.match(name)

    @pytest.mark.parametrize("name", [
        "../../../../etc/passwd",
        "../../secrets.json",
        "/etc/passwd",             # an absolute component makes os.path.join
                                   # DISCARD the base dir - traversable with a
                                   # single leading slash, not only with "../"
        "..%2f..%2fetc%2fpasswd",
        "index.m3u8/../../../etc/passwd",
        "....//etc/passwd",
        "a\\..\\..\\windows\\win.ini",
        "index.m3u8\x00.txt",
        ".env",
        "index.exe",
        "",
    ])
    def test_traversal_and_unexpected_extensions_are_rejected(self, name):
        assert not api._HLS_FILE_RE.match(name)

    def test_the_pattern_admits_no_path_separator_at_all(self):
        assert not any(api._HLS_FILE_RE.match(n) for n in ("a/b.ts", "a\\b.ts"))


# --------------------------------------------------------------------------- #
# SEC-020 - SQL injection through the NGSI-LD tenant
# --------------------------------------------------------------------------- #
class TestSchemaNameValidation:
    @pytest.mark.parametrize("schema", [
        "platformts_gijon", "platformts_t1", "platformts_a_b_c", "abc123",
    ])
    def test_legitimate_names_pass(self, schema):
        assert validate_schema_name(schema) == schema

    @pytest.mark.parametrize("payload", [
        "platformts_x; DROP SCHEMA public CASCADE; --",
        "platformts_x'; DROP SCHEMA public CASCADE; --",
        'platformts_x"; DROP SCHEMA public CASCADE; --',
        "platformts_x--",
        "platformts_x/*c*/",
        "platformts_X",             # uppercase folds in unquoted SQL
        "platformts_x y",
        "platformts_x\nDROP SCHEMA public",
        "",                         # empty is not a valid identifier
        "platformts_ñ",
    ])
    def test_hostile_or_odd_names_are_refused(self, payload):
        with pytest.raises(InvalidSchemaName):
            validate_schema_name(payload)

    def test_over_long_names_are_refused_not_truncated(self):
        """PostgreSQL truncates at 63 bytes, which would collide two tenants."""
        with pytest.raises(InvalidSchemaName):
            validate_schema_name("a" * 64)

    def test_the_rendered_sql_contains_no_injected_statement(self):
        with pytest.raises(InvalidSchemaName):
            render_check_schema("platformts_x; DROP SCHEMA public CASCADE; --")

    def test_identifier_positions_are_quoted(self):
        sql = render_check_schema("platformts_gijon")
        assert 'CREATE SCHEMA "platformts_gijon";' in sql
        # ... and the string-literal positions are NOT quoted, or the lookup breaks
        assert "where schema_name = 'platformts_gijon'" in sql

    def test_quote_identifier_doubles_embedded_quotes(self):
        assert quote_identifier('a"b') == '"a""b"'

    def test_the_rendered_script_has_a_single_statement_terminator_shape(self):
        """A crude but effective canary: no stray semicolon-comment sequences."""
        sql = render_check_schema("platformts_gijon")
        assert "--;" not in sql
        assert "DROP SCHEMA public" not in sql


# --------------------------------------------------------------------------- #
# SEC-045 - predictable correlation ids
# --------------------------------------------------------------------------- #
class TestQueueUuid:
    def test_uuid_is_version_4(self):
        """
        uuid1() encodes the host MAC address and a timestamp: it leaks the node
        identity and neighbouring ids are guessable.
        """
        assert uuid.UUID(Queue().uuid).version == 4

    def test_ids_do_not_share_a_mac_derived_suffix(self):
        ids = [uuid.UUID(Queue().uuid) for _ in range(20)]
        # uuid1 puts the (constant) node id in the last 48 bits.
        assert len({u.int & 0xFFFFFFFFFFFF for u in ids}) == len(ids)
