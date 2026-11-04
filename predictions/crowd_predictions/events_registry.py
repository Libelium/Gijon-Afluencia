"""
Manual registry of punctual events (markets, fairs, concerts...) - unlike
holidays/high season (training_data.py, via a library/fixed date ranges), an
event cannot be computed, someone has to know it is happening and record it.

What it is for: the days of an event are NOT normal, so the model must not learn
from them. training_data.mask_event_bins() drops them as training rows and swaps
their occupancy for the zone's usual one before any lag/rolling is computed, in
training and in prediction alike - otherwise a week-long market would still
inflate the lag_1w/rolling_mean_7d of the week after. The model predicts the
normal day; the event itself is drawn on top by the prediction panel's scenario
simulator, which receives the registered events through the `registeredEvents`
attribute that etl/predict/transform.py publishes on each prediction entity.

Stored as a small CSV blob in storage (S3/MinIO), UNDER THE SAME PREFIX AS THE
MODEL (settings.storage().MODELS_PREFIX) - not a prefix of its own. There is
no live CRUD entry point (decided with the team: it would need per-tenant
write permissions on the bucket that only the admin has, more machinery than
this is worth); whoever maintains the bucket uploads/edits this CSV by hand,
the same way the model gets uploaded - one route to remember, not two.
Segregated by tenant/scope like the model (see
helpers/model_storage.segregated_key) - NOT a local file: a plain path would
depend on the machine that runs it, exactly what removing FilesystemStorage
was for. Columns: date,event_type,device_ids,notes,end_date,start_hour,end_hour
(the last three optional - a file with only the first four is still valid).
  - date / end_date: LOCAL calendar days, ISO. end_date empty = a one-day event;
    a week-long market is one row from its first day to its last.
  - event_type: free text. The panel's simulator uses it when it matches one of
    its event kinds (market, concert, festival...); it does not affect training.
  - device_ids: optional, comma-separated list of affected zones (empty =
    GLOBAL, affects every zone that day; e.g. a market only happening in 2 of
    every zone). MUST be the NGSI-LD `CrowdFlowZone` entity URN
    ("urn:ngsi-ld:CrowdFlowZone:<zone_id>"), matching `zone_id` elsewhere in this
    repo - training_data.py gets `zone_id` from Aether's entity "id" (see
    helpers/aether_history.py::resolve_zone_ids), which already IS the URN. A URN
    is only guaranteed unique WITHIN a tenant+scope, not across the whole
    platform - harmless here because this registry is already segregated by
    tenant/scope (see events_registry_key), so two tenants sharing a URN string
    still get two separate CSVs, one entry each.
  - start_hour / end_hour: optional local hours (0-24) for the simulator to draw
    the event; training always leaves out the WHOLE day.
"""
import csv
import hashlib
import io
import logging
import os
from datetime import date as date_cls, timedelta

from crowd_predictions.config import settings
from crowd_predictions.config.config import get_storage
from crowd_predictions.helpers.model_storage import segregated_key

logger = logging.getLogger(__name__)

CACHE_FILENAME = "events_registry.csv"
FIELDNAMES = ["date", "event_type", "device_ids", "notes", "end_date", "start_hour", "end_hour"]


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


def _parse_hour(raw: str, field: str, index: int):
    """A local hour 0-24, None if empty. A bad value only loses the hour (the
    simulator falls back to its default), never the event itself."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        hour = int(raw)
    except ValueError:
        hour = -1
    if not 0 <= hour <= 24:
        logger.warning(f"Ignoring events_registry row {index} {field} {raw!r} - not an hour 0-24")
        return None
    return hour


def load_events_registry(storage, local_dir: str = "/tmp") -> list:
    """
    -> [{"date" (date), "end_date" (date, == date for a one-day event),
    "device_ids" (set or None if global), "event_type", "notes",
    "start_hour"/"end_hour" (int or None)}].

    [] if nothing has been uploaded yet (cold start) - not an
    error - the normal state before the first event is recorded.
    A single malformed row (typically a bad date - "2026-8-4" instead of
    "2026-08-04", or an end_date before its date) is SKIPPED with a WARNING, not
    fatal to the whole registry: _cached_events_registry's broad except
    (training_data.py) is meant for "storage unreachable", not "row 7 has a typo" -
    without this, one bad row would silently empty every OTHER correctly written
    event too.
    """
    text = _download_csv_text(storage, local_dir)
    if not text:
        return []
    events = []
    for index, row in enumerate(csv.DictReader(io.StringIO(text))):
        raw_date = (row.get("date") or "").strip()
        if not raw_date:
            continue  # blank row, skip
        raw_end = (row.get("end_date") or "").strip()
        try:
            parsed_date = date_cls.fromisoformat(raw_date)
            end_date = date_cls.fromisoformat(raw_end) if raw_end else parsed_date
        except ValueError:
            logger.warning(f"Skipping events_registry row {index} - invalid date {raw_date!r}/{raw_end!r}")
            continue
        if end_date < parsed_date:
            logger.warning(f"Skipping events_registry row {index} - end_date {raw_end!r} before {raw_date!r}")
            continue
        device_ids_raw = (row.get("device_ids") or "").strip()
        device_ids = {d.strip() for d in device_ids_raw.split(",") if d.strip()} or None
        events.append({
            "date": parsed_date,
            "end_date": end_date,
            "device_ids": device_ids,
            "event_type": (row.get("event_type") or "").strip(),
            "notes": (row.get("notes") or "").strip(),
            "start_hour": _parse_hour(row.get("start_hour"), "start_hour", index),
            "end_hour": _parse_hour(row.get("end_hour"), "end_hour", index),
        })
    return events


def _applies_to(event: dict, zone_id: str) -> bool:
    """A GLOBAL event (device_ids=None) applies to ANY zone; one with device_ids
    set only to those listed (e.g. a market only happening in some zones)."""
    return event["device_ids"] is None or zone_id in event["device_ids"]


def _days_of(event: dict):
    day = event["date"]
    while day <= event["end_date"]:
        yield day
        day += timedelta(days=1)


def event_days(zone_id: str, events: list) -> set:
    """The local days on which `zone_id` has an event - what training must leave out.
    Overlapping events simply share their days."""
    return {day for event in events if _applies_to(event, zone_id) for day in _days_of(event)}


def events_in_window(zone_id: str, first_day, last_day, events: list) -> list:
    """The events of `zone_id` touching the local days [first_day, last_day], in date
    order - what the prediction entity publishes for the panel."""
    return sorted(
        (e for e in events
         if _applies_to(e, zone_id) and e["date"] <= last_day and e["end_date"] >= first_day),
        key=lambda e: (e["date"], e["end_date"], e["event_type"]),
    )


def fingerprint(events: list, until=None) -> str:
    """
    "len:hash" of what decides WHICH ROWS training leaves out: each event's days
    and zones. NOT event_type, notes or hours - they only change what the panel
    draws, not the trained model.

    `until` (a local date): only the days up to it count - the days a model whose
    data reaches `until` has already learned. An event entirely after it does not
    change the fingerprint, and one crossing it only by its days up to it: so
    registering, moving or deleting an event AHEAD of time leaves a stored model
    alone, and its days are left out by the warm start's own window when they come.
    A retroactive change (a fair added for days already trained on) does change it -
    see warm_start.events_registry_changed(), which then forces the full retrain
    that is the only way to unlearn those days. None = every day (the whole registry).

    Deliberately NOT Python's hash(): it is randomized per process
    (PYTHONHASHSEED), so the SAME unchanged registry would fingerprint
    differently on every cron invocation and look "changed" forever.
    """
    rows = []
    for e in events:
        if until is not None and e["date"] > until:
            continue
        end = e["end_date"] if until is None else min(e["end_date"], until)
        zones = ",".join(sorted(e["device_ids"])) if e["device_ids"] else ""
        rows.append(f"{e['date'].isoformat()}:{end.isoformat()}:{zones}")
    digest = hashlib.sha256("|".join(sorted(rows)).encode("utf-8")).hexdigest()[:16]
    return f"{len(rows)}:{digest}"


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
            "end_date": (row.get("end_date") or "").strip(),
            "start_hour": (row.get("start_hour") or "").strip(),
            "end_hour": (row.get("end_hour") or "").strip(),
        })
    return rows


def append_event(storage, date_str: str, event_type: str, device_ids: str = "",
                 notes: str = "", end_date: str = "", start_hour=None, end_hour=None,
                 local_dir: str = "/tmp") -> None:
    """
    Appends a row to the registry in storage. Validates the dates (real ISO dates,
    end_date not before date) and the hours before writing - fails fast and clear if
    the caller sends garbage, instead of leaving a row load_events_registry() skips.
    A registry written with the old four columns gets the new header first, its rows
    keeping their values.

    A caller running in a process that keeps serving afterwards (a CRUD
    endpoint, not a short-lived script) must call training_data.clear_caches()
    after this - otherwise this write is invisible until the process restarts
    (training_data._cached_events_registry is per-process). Not done HERE:
    events_registry.py cannot import training_data.py (training_data.py
    already imports this module - the other way around would be a cycle).
    """
    first = date_cls.fromisoformat(date_str)
    if end_date and date_cls.fromisoformat(end_date) < first:
        raise ValueError(f"end_date {end_date!r} is before date {date_str!r}")
    for hour in (start_hour, end_hour):
        if hour is not None and not 0 <= int(hour) <= 24:
            raise ValueError(f"{hour!r} is not an hour 0-24")

    rows = list(csv.DictReader(io.StringIO(_download_csv_text(storage, local_dir))))
    rows.append({
        "date": date_str, "event_type": event_type, "device_ids": device_ids, "notes": notes,
        "end_date": end_date,
        "start_hour": "" if start_hour is None else str(int(start_hour)),
        "end_hour": "" if end_hour is None else str(int(end_hour)),
    })

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDNAMES, extrasaction="ignore", restval="")
    writer.writeheader()
    writer.writerows(rows)
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
