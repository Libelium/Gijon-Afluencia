"""
Regression tests for SEC-024 and SEC-025.

Both findings are reappearances - they were SEC-002 and SEC-010 of the first
audited delivery - and neither had a test pinning the behaviour, which is how
they came back. These are those tests.
"""

import gzip
import hmac
import zlib

import pytest

from app.api.v1.routes import ote_data_router
from app.core.ote.raw_ote_archiver import decode_body, decompress_bounded


# --------------------------------------------------------------------------- #
# SEC-024 - decompression bomb
# --------------------------------------------------------------------------- #
def _bomb(size: int) -> bytes:
    """A gzip body whose output is `size` bytes of zeros - it compresses ~1000:1."""
    return gzip.compress(b"\x00" * size)


class TestBoundedDecompression:
    def test_a_normal_body_still_round_trips(self):
        payload = b'{"a": 1}\n'
        assert decompress_bounded(gzip.compress(payload), 1024 * 1024) == payload

    def test_output_over_the_ceiling_is_refused(self):
        # 8 MB of output against a 1 MB ceiling.
        assert decompress_bounded(_bomb(8 * 1024 * 1024), 1024 * 1024) is None

    def test_exactly_at_the_ceiling_is_accepted(self):
        size = 64 * 1024
        assert len(decompress_bounded(_bomb(size), size)) == size

    def test_the_compressed_body_stays_small_while_the_output_does_not(self):
        """The point of the finding: input size is no proxy for memory cost."""
        bomb = _bomb(16 * 1024 * 1024)
        assert len(bomb) < 32 * 1024          # a few KB on the wire ...
        assert decompress_bounded(bomb, 1024 * 1024) is None   # ... 16 MB off it

    def test_truncated_stream_raises_instead_of_looping(self):
        with pytest.raises(zlib.error):
            decompress_bounded(gzip.compress(b"x" * 4096)[:20], 1024 * 1024)

    def test_decode_body_drops_a_bomb(self, monkeypatch):
        """End to end through the archiver's entry point."""
        from app.core.ote import raw_ote_archiver

        monkeypatch.setattr(
            raw_ote_archiver.settings, "OTE_MAX_DECOMPRESSED_BYTES", 64 * 1024
        )
        assert decode_body(_bomb(4 * 1024 * 1024)) is None

    def test_decode_body_still_accepts_a_real_frame(self, monkeypatch):
        from app.core.ote import raw_ote_archiver

        monkeypatch.setattr(
            raw_ote_archiver.settings, "OTE_MAX_DECOMPRESSED_BYTES", 64 * 1024
        )
        frame = b'{"id": "lib-01", "objects": []}'
        assert decode_body(gzip.compress(frame)) == frame + b"\n"


# --------------------------------------------------------------------------- #
# SEC-025 - fail-open authentication and the token in the query string
# --------------------------------------------------------------------------- #
class FakeRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}
        self.client = None


class TestOteIngestAuthorisation:
    def test_unconfigured_token_denies_instead_of_allowing(self, monkeypatch):
        """
        The heart of SEC-025: `if not expected: return True`. An empty secret is
        the default in the chart, so the endpoint shipped open.
        """
        monkeypatch.setattr(ote_data_router.settings, "OTE_WEBHOOK_TOKEN", "")
        assert ote_data_router._authorised(FakeRequest()) is False

    def test_unconfigured_token_denies_even_with_a_header_supplied(self, monkeypatch):
        monkeypatch.setattr(ote_data_router.settings, "OTE_WEBHOOK_TOKEN", "")
        request = FakeRequest({"x-ote-token": "anything"})
        assert ote_data_router._authorised(request) is False

    def test_correct_header_is_accepted(self, monkeypatch):
        monkeypatch.setattr(ote_data_router.settings, "OTE_WEBHOOK_TOKEN", "s3cret")
        request = FakeRequest({"x-ote-token": "s3cret"})
        assert ote_data_router._authorised(request) is True

    def test_wrong_header_is_rejected(self, monkeypatch):
        monkeypatch.setattr(ote_data_router.settings, "OTE_WEBHOOK_TOKEN", "s3cret")
        request = FakeRequest({"x-ote-token": "nope"})
        assert ote_data_router._authorised(request) is False

    def test_missing_header_is_rejected(self, monkeypatch):
        monkeypatch.setattr(ote_data_router.settings, "OTE_WEBHOOK_TOKEN", "s3cret")
        assert ote_data_router._authorised(FakeRequest()) is False

    def test_the_route_no_longer_accepts_a_token_query_parameter(self):
        """
        A secret in the URL leaks into every access log, proxy log and Referer
        on the path. `t=` must not be a parameter of the handler any more.
        """
        import inspect

        params = inspect.signature(ote_data_router.ote_ingest).parameters
        assert "t" not in params
        assert set(params) == {"device_id", "request"}

    def test_authorisation_helper_takes_no_token_argument(self):
        import inspect

        assert list(inspect.signature(ote_data_router._authorised).parameters) == [
            "request"
        ]

    def test_comparison_is_constant_time(self):
        """`==` on secrets leaks their prefix through timing."""
        import inspect

        source = inspect.getsource(ote_data_router._authorised)
        assert "hmac.compare_digest" in source
