"""Receiver for the LIDAR Object Tracking Events (AMORPH.senses) push API.

The sensor treats any non-2xx as a failed delivery, so this answers 200 at once and
queues the body for core/ote/raw_ote_archiver.py. Never parsed here: a parse error must
not become a non-2xx, and the vendor may add fields without notice.
"""

import hmac

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.core.config.config import settings
from app.core.config.logging import appLogging as log
from app.core.ote.raw_ote_archiver import archiver

router = APIRouter()


def _authorised(request: Request) -> bool:
    """
    Shared secret from the `X-OTE-Token` header.

    SEC-025. Two things changed here, both reappearances from the first audit.

    Fail-closed. This used to read `if not expected: return True`, i.e. an
    unconfigured `OTE_WEBHOOK_TOKEN` - the default, since it has no value in the
    chart - authorised *everyone*. An authorisation function whose failure mode
    is "allow" is not an authorisation function; a missing secret is a
    deployment error and is now reported as one.

    No token in the query string. The `t=` parameter is gone. A secret in a URL
    is written to every access log along the path, to the reverse proxy's log, to
    any Referer sent by an intermediary and to crash reports, and unlike a header
    it survives in stored URLs. Senders that cannot set a header need a different
    credential, not a leaked one.
    """
    expected = settings.OTE_WEBHOOK_TOKEN
    if not expected:
        log.error(
            "OTE ingest: OTE_WEBHOOK_TOKEN is not configured - rejecting the "
            "request. Set it on this service and on every sensor."
        )
        return False
    received = request.headers.get("x-ote-token") or ""
    return hmac.compare_digest(received, expected)


@router.post("/{device_id}", status_code=200)
async def ote_ingest(device_id: str, request: Request):
    """Queues one tracking frame for `device_id`, the free label that partitions the
    archive. One URL per sensor, so the body never has to be parsed to know who sent it."""
    if not _authorised(request):
        log.error("OTE ingest: bad token for device %r from %s", device_id,
                  request.client.host if request.client else "unknown")
        return Response(status_code=401)

    try:
        archiver.add(device_id, await request.body())
    except Exception as e:
        # 200 even on failure: a non-2xx makes the sender retry and duplicate the frame.
        log.error("OTE ingest: could not queue frame for %s: %s", device_id, e)

    return Response(status_code=200)
