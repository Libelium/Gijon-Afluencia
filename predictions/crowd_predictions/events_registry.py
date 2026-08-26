"""
Manual registry of punctual events (markets, fairs, concerts...) - unlike
holidays/high season (training_data.py, via a library/fixed date ranges), an
event cannot be computed, someone has to know it is happening and record it.

Stored as a small CSV blob in storage (S3/MinIO), UNDER THE SAME PREFIX AS THE
MODEL (settings.storage().MODELS_PREFIX) - not a prefix of its own. There is
no live CRUD entry point (decided with the team: it would need per-tenant
write permissions on the bucket that only the admin has, more machinery than
this is worth); whoever maintains the bucket uploads/edits this CSV by hand,
the same way the model gets uploaded - one route to remember, not two.
Segregated by tenant/scope like the model (see
helpers/model_storage.segregated_key) - NOT a local file: a plain path would
depend on the machine that runs it, exactly what removing FilesystemStorage
was for. Columns: date,event_type,device_ids,notes.
  - event_type: free text ("small_event", "large_event", whatever is needed) -
    see event_magnitudes() for the numeric weight per type.
  - device_ids: optional, comma-separated list of affected zones (empty =
    GLOBAL, affects every zone that day; e.g. a market only happening in 2 of
    every zone). MUST be the NGSI-LD `CrowdFlowZone` entity URN
    ("urn:ngsi-ld:CrowdFlowZone:<zone_id>"), matching `zone_id` elsewhere in this
    repo - training_data.py/add_calendar_features() gets `zone_id` from
    Aether's entity "id" (see helpers/aether_history.py::resolve_zone_ids),
    which already IS the URN. A URN is only guaranteed unique WITHIN a
    tenant+scope, not across the whole platform - harmless here because this
    registry is already segregated by tenant/scope (see events_registry_key),
    so two tenants sharing a URN string still get two separate CSVs, one
    entry each.

With few rows the model will barely learn anything from this yet (thin
signal) - the point is to start accumulating the data NOW in the right shape,
so that months from now, with more events recorded, the model has something
to learn from. It does no harm meanwhile: a date/device with no entry ->
magnitude 0, same as today.
"""
import csv
import hashlib
import io
import logging
import os
from datetime import date as date_cls

from crowd_predictions.config import settings
from crowd_predictions.config.config import get_storage
from crowd_predictions.helpers.model_storage import segregated_key

logger = logging.getLogger(__name__)

CACHE_FILENAME = "events_registry.csv"
FIELDNAMES = ["date", "event_type", "device_ids", "notes"]

# Numeric weight per event type - EXTENSIBLE, not a closed enum in code. An
# event_type not listed here uses DEFAULT_MAGNITUDE (1, "there is an event but
# we do not know how to weigh it yet"). EVENT_MAGNITUDES overrides and extends
# this per deployment, so a new event type no longer needs a code change.
BUILTIN_EVENT_MAGNITUDE = {
    "small_event": 1,
    "large_event": 2,
}
DEFAULT_MAGNITUDE = 1


def event_magnitudes() -> dict:
    """The built-in weights with the deployment's overrides applied."""
    return {**BUILTIN_EVENT_MAGNITUDE, **settings.events().magnitudes()}


def events_registry_key() -> str:
    """Same prefix as the model (settings.storage().MODELS_PREFIX) - see the
    module docstring for why this is deliberately not its own prefix."""
    return segregated_key(settings.storage().MODELS_PREFIX, CACHE_FILENAME)


def _download_csv_text(storage, local_dir: str) -> str:
    """The registry as raw CSV text, or "" if nothing has been uploaded yet
    (cold start, same contract as helpers/model_storage.load_model_bundle)."""
    local_path = os.path.join(local_dir, CACHE_FILENAME)
    try:
        storage.download_file(events_registry_key(), local_path)
    except Exception as e:
        logger.warning(f"No events registry in storage ('{events_registry_key()}': {e})")
        return ""
    with open(local_path, encoding="utf-8") as f:
        return f.read()


def _upload_csv_text(storage, text: str, local_dir: str) -> None:
    local_path = os.path.join(local_dir, CACHE_FILENAME)
    with open(local_path, "w", newline="", encoding="utf-8") as f:
        f.write(text)
    storage.upload_file(events_registry_key(), local_path)


def load_events_registry(storage, local_dir: str = "/tmp") -> list:
    """
    -> [{"date" (date), "magnitude" (int), "device_ids" (set or None if
    global), "event_type", "notes"}].

    No registry uploaded yet, or an empty one (header only) -> [], not an
    error - the normal state before the first event is recorded.

    A single malformed row (typically a bad date - "2026-8-4" instead of
    "2026-08-04") is SKIPPED with a WARNING, not fatal to the whole registry:
    _cached_events_registry's broad except (training_data.py) is meant for
    "storage unreachable", not "row 7 has a typo" - without this, one bad row
    would silently empty every OTHER correctly written event too.
    """
    text = _download_csv_text(storage, local_dir)
    if not text:
        return []

    events = []
    magnitudes = event_magnitudes()   # read once per parse, not once per row
    for index, row in enumerate(csv.DictReader(io.StringIO(text))):
        raw_date = (row.get("date") or "").strip()
        if not raw_date:
            continue  # blank row, skip

        try:
            parsed_date = date_cls.fromisoformat(raw_date)
        except ValueError:
            logger.warning(f"Skipping events_registry row {index} - invalid date {raw_date!r}")
            continue

        device_ids_raw = (row.get("device_ids") or "").strip()
        device_ids = {d.strip() for d in device_ids_raw.split(",") if d.strip()} or None

        event_type = (row.get("event_type") or "").strip()
        events.append({
            "date": parsed_date,
            "magnitude": magnitudes.get(event_type, DEFAULT_MAGNITUDE),
            "device_ids": device_ids,
            "event_type": event_type,
            "notes": (row.get("notes") or "").strip(),
        })

    return events


def event_magnitude_for(zone_id: str, target_date, events: list) -> int:
    """
    Magnitude (the highest) of the event(s) that apply to `zone_id` on
    `target_date`, 0 if none. A GLOBAL event (device_ids=None in the registry)
    applies to ANY zone; one with device_ids set only applies to those listed
    (e.g. a market only happening in some of the zones, not all of them).

    If two events coincide on the same day over the same zone, the LARGER
    magnitude wins (never summed - a day with both a fair AND a market is
    still, at most, "the biggest event that day").
    """
    matching = [
        e["magnitude"] for e in events
        if e["date"] == target_date and (e["device_ids"] is None or zone_id in e["device_ids"])
    ]
    return max(matching, default=0)


def fingerprint(events: list) -> str:
    """
    "len:hash" of the (date, event_type, device_ids) that actually feed
    event_magnitude_for() - NOT notes, which does not affect the trained
    feature. Changes on any edit to the REGISTRY FILE: a new row, a deleted
    one, or a RETROACTIVE change to a past row (a fair added for a date already
    trained on) - see warm_start.events_registry_changed(), which forces a full
    retrain when this changes, the same way blocking_column_change does for the
    columns themselves.

    Hashes the MAGNITUDE, not the event_type: re-weighing a type (in code or via
    EVENT_MAGNITUDES) changes every row's trained value without editing the file,
    and hashing the type left the fingerprint identical through it.

    Deliberately NOT Python's hash(): it is randomized per process
    (PYTHONHASHSEED), so the SAME unchanged registry would fingerprint
    differently on every cron invocation and look "changed" forever.
    """
    canonical = "|".join(sorted(
        f"{e['date'].isoformat()}:{e['event_type']}:{e['magnitude']}:"
        f"{','.join(sorted(e['device_ids'])) if e['device_ids'] else ''}"
        for e in events
    ))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"{len(events)}:{digest}"


def list_raw_rows(storage, local_dir: str = "/tmp") -> list:
    """
    Rows of the registry with their index (0-based, file order) as plain text
    (not parsed to date/set like load_events_registry) - for listing/deleting
    from a CRUD without assuming dates are unique (two events can share a date).
    """
    text = _download_csv_text(storage, local_dir)
    if not text:
        return []

    rows = []
    for i, row in enumerate(csv.DictReader(io.StringIO(text))):
        if not (row.get("date") or "").strip():
            continue
        rows.append({
            "index": i,
            "date": (row.get("date") or "").strip(),
            "event_type": (row.get("event_type") or "").strip(),
            "device_ids": (row.get("device_ids") or "").strip(),
            "notes": (row.get("notes") or "").strip(),
        })
    return rows


def append_event(storage, date_str: str, event_type: str, device_ids: str = "",
                 notes: str = "", local_dir: str = "/tmp") -> None:
    """
    Appends a row to the registry in storage. Validates that `date_str` is a
    real ISO date before writing - fails fast and clear if the caller sends
    garbage, instead of leaving a row event_magnitude_for() could not read.

    A caller running in a process that keeps serving afterwards (a CRUD
    endpoint, not a short-lived script) must call training_data.clear_caches()
    after this - otherwise this write is invisible until the process restarts
    (training_data._cached_events_registry is per-process). Not done HERE:
    events_registry.py cannot import training_data.py (training_data.py
    already imports this module - the other way around would be a cycle).
    """
    date_cls.fromisoformat(date_str)

    text = _download_csv_text(storage, local_dir)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    if not text:
        writer.writerow(FIELDNAMES)
    else:
        buffer.write(text if text.endswith("\n") else text + "\n")
    writer.writerow([date_str, event_type, device_ids, notes])

    _upload_csv_text(storage, buffer.getvalue(), local_dir)


def delete_event_at_index(storage, index: int, local_dir: str = "/tmp") -> bool:
    """Deletes row `index` (0-based, same order as list_raw_rows) - rewrites
    the whole registry without that row. False if the index does not exist.
    Same cache-invalidation note as append_event."""
    text = _download_csv_text(storage, local_dir)
    if not text:
        return False

    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return False
    header, data_rows = rows[0], rows[1:]
    if index < 0 or index >= len(data_rows):
        return False
    del data_rows[index]

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(data_rows)
    _upload_csv_text(storage, buffer.getvalue(), local_dir)
    return True
