import os
from datetime import date
from unittest.mock import patch

from crowd_predictions.events_registry import (
    load_events_registry, event_magnitude_for, list_raw_rows, append_event,
    delete_event_at_index, events_registry_key, DEFAULT_MAGNITUDE,
)


def test_registry_key_is_segregated_by_tenant_and_scope():
    with patch.dict(os.environ, {"FIWARE_TENANT": "libelium", "FIWARE_SCOPE": "tenant_a"}):
        assert events_registry_key() == "prediction-models/libelium/tenant_a/events_registry.csv"


def test_registry_key_lives_under_the_same_prefix_as_the_model():
    """Decided with the team (point 7): no CRUD entry point, uploaded by hand -
    same route as the model, not a prefix of its own to remember."""
    from crowd_predictions.helpers.model_storage import model_storage_key
    with patch.dict(os.environ, {"FIWARE_TENANT": "libelium", "FIWARE_SCOPE": "tenant_a"}):
        model_key = model_storage_key("crowd_xgboost_model.json")
        registry_key = events_registry_key()
    assert model_key.rsplit("/", 1)[0] == registry_key.rsplit("/", 1)[0]


class _DictStorage:
    """The StorageType contract in memory. download_file RAISES when the key is
    missing, which is how the registry tells "never written" from "has rows"."""

    def __init__(self):
        self.files = {}

    def upload_file(self, filename, path):
        with open(path, "rb") as f:
            self.files[filename] = f.read()
        return path

    def download_file(self, filename, path):
        if filename not in self.files:
            raise FileNotFoundError(filename)
        with open(path, "wb") as f:
            f.write(self.files[filename])
        return path

    def delete_file(self, path):
        self.files.pop(path, None)
        return True

    def list_all(self):
        return sorted(self.files)


def _tenant_scope():
    return patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"})


def test_load_events_registry_with_nothing_uploaded_yet_returns_empty_list(tmp_path):
    with _tenant_scope():
        assert load_events_registry(_DictStorage(), local_dir=str(tmp_path)) == []


def test_append_then_load_parses_a_global_event_empty_device_ids(tmp_path):
    storage = _DictStorage()
    with _tenant_scope():
        append_event(storage, "2026-04-09", "large_event", "", "Concert", local_dir=str(tmp_path))
        events = load_events_registry(storage, local_dir=str(tmp_path))

    assert len(events) == 1
    assert events[0]["date"] == date(2026, 4, 9)
    assert events[0]["magnitude"] == 2
    assert events[0]["device_ids"] is None  # None = global, not an empty set


def test_append_then_load_parses_a_scoped_event_device_ids_list(tmp_path):
    storage = _DictStorage()
    with _tenant_scope():
        append_event(storage, "2026-09-02", "small_event", "SS3,SS7,SS11", "Market", local_dir=str(tmp_path))
        events = load_events_registry(storage, local_dir=str(tmp_path))

    assert events[0]["device_ids"] == {"SS3", "SS7", "SS11"}
    assert events[0]["magnitude"] == 1


def test_unknown_event_type_uses_the_default_magnitude(tmp_path):
    storage = _DictStorage()
    with _tenant_scope():
        append_event(storage, "2026-10-01", "concert", "", "Concert in the square", local_dir=str(tmp_path))
        events = load_events_registry(storage, local_dir=str(tmp_path))
    assert events[0]["magnitude"] == DEFAULT_MAGNITUDE


def test_append_rejects_an_invalid_date(tmp_path):
    storage = _DictStorage()
    with _tenant_scope():
        try:
            append_event(storage, "15-08-2026", "large_event", local_dir=str(tmp_path))
            assert False, "should have raised ValueError"
        except ValueError:
            pass
    assert storage.files == {}  # nothing written on a rejected input


def _upload_raw_csv(storage, text: str):
    """Bypasses append_event's own validation - simulates a bad row that
    already made it into storage some other way (a hand-edited CSV, a bug in
    an older version of append_event, direct S3 console edit...)."""
    with _tenant_scope():
        storage.files[events_registry_key()] = text.encode("utf-8")


def test_a_malformed_date_skips_only_that_row_not_the_whole_registry(tmp_path, caplog):
    storage = _DictStorage()
    csv_text = (
        "date,event_type,device_ids,notes\n"
        "2026-04-09,large_event,,Concert\n"
        "2026-8-4,small_event,,Typo'd month\n"  # invalid - would raise on fromisoformat
        "2026-09-02,small_event,SS3,Market\n"
    )
    _upload_raw_csv(storage, csv_text)

    with _tenant_scope():
        with caplog.at_level("WARNING"):
            events = load_events_registry(storage, local_dir=str(tmp_path))

    assert [e["date"] for e in events] == [date(2026, 4, 9), date(2026, 9, 2)]
    assert "Skipping events_registry row 1" in caplog.text
    assert "2026-8-4" in caplog.text


def test_multiple_appends_accumulate_rows_across_uploads(tmp_path):
    """Each append downloads-modifies-uploads - the second append must see the
    first one's row, not overwrite it."""
    storage = _DictStorage()
    with _tenant_scope():
        append_event(storage, "2026-04-09", "large_event", local_dir=str(tmp_path))
        append_event(storage, "2026-09-02", "small_event", "SS3", local_dir=str(tmp_path))
        events = load_events_registry(storage, local_dir=str(tmp_path))
    assert len(events) == 2


def test_list_raw_rows_returns_index_and_raw_fields(tmp_path):
    storage = _DictStorage()
    with _tenant_scope():
        append_event(storage, "2026-04-09", "large_event", "", "Concert", local_dir=str(tmp_path))
        append_event(storage, "2026-09-02", "small_event", "SS3,SS7", "Market", local_dir=str(tmp_path))
        rows = list_raw_rows(storage, local_dir=str(tmp_path))

    assert [r["index"] for r in rows] == [0, 1]
    assert rows[1]["device_ids"] == "SS3,SS7"
    assert rows[1]["event_type"] == "small_event"


def test_delete_event_at_index_removes_only_that_row(tmp_path):
    storage = _DictStorage()
    with _tenant_scope():
        append_event(storage, "2026-04-09", "large_event", local_dir=str(tmp_path))
        append_event(storage, "2026-09-02", "small_event", local_dir=str(tmp_path))
        assert delete_event_at_index(storage, 0, local_dir=str(tmp_path)) is True
        rows = list_raw_rows(storage, local_dir=str(tmp_path))

    assert len(rows) == 1
    assert rows[0]["date"] == "2026-09-02"
    assert rows[0]["index"] == 0  # re-indexed after the delete, not the original 1


def test_delete_event_at_index_out_of_range_returns_false_and_does_not_touch_storage(tmp_path):
    storage = _DictStorage()
    with _tenant_scope():
        append_event(storage, "2026-04-09", "large_event", local_dir=str(tmp_path))
        before = dict(storage.files)
        assert delete_event_at_index(storage, 5, local_dir=str(tmp_path)) is False
    assert storage.files == before


def test_delete_event_at_index_with_nothing_uploaded_returns_false(tmp_path):
    with _tenant_scope():
        assert delete_event_at_index(_DictStorage(), 0, local_dir=str(tmp_path)) is False


def test_event_magnitude_for_global_event_applies_to_any_device():
    events = [{"date": date(2026, 4, 9), "magnitude": 2, "device_ids": None}]
    assert event_magnitude_for("SS1", date(2026, 4, 9), events) == 2
    assert event_magnitude_for("L23", date(2026, 4, 9), events) == 2


def test_event_magnitude_for_scoped_event_only_applies_to_listed_devices():
    events = [{"date": date(2026, 9, 2), "magnitude": 1, "device_ids": {"SS3", "SS7", "SS11"}}]
    assert event_magnitude_for("SS3", date(2026, 9, 2), events) == 1
    assert event_magnitude_for("SS4", date(2026, 9, 2), events) == 0  # same zone, NOT a listed device


def test_device_ids_is_the_ngsi_ld_urn_not_the_short_ss_code(tmp_path):
    """device_id in training_data.py comes from Aether's entity "id" (see
    helpers/aether_history.py::resolve_device_ids) - already a URN, not the
    "SS1"-style shorthand zones_config.py uses for the synthetic fixtures. The
    registry has to be written in that same identifier space to ever match."""
    urn = "urn:ngsi-ld:CrowdFlowObserved:SPT0123456789ABCDEF01234567_CFO"
    storage = _DictStorage()
    with _tenant_scope():
        append_event(storage, "2026-04-09", "large_event", urn, "Concert", local_dir=str(tmp_path))
        events = load_events_registry(storage, local_dir=str(tmp_path))

    assert events[0]["device_ids"] == {urn}
    assert event_magnitude_for(urn, date(2026, 4, 9), events) == 2
    assert event_magnitude_for("SS1", date(2026, 4, 9), events) == 0  # the short code is NOT the URN


def test_event_magnitude_for_no_matching_date_returns_zero():
    events = [{"date": date(2026, 4, 9), "magnitude": 2, "device_ids": None}]
    assert event_magnitude_for("SS1", date(2026, 8, 16), events) == 0


def test_event_magnitude_for_two_events_same_day_keeps_the_larger_not_the_sum():
    events = [
        {"date": date(2026, 4, 9), "magnitude": 2, "device_ids": None},        # global fair
        {"date": date(2026, 4, 9), "magnitude": 1, "device_ids": {"SS3"}},     # + a punctual market
    ]
    assert event_magnitude_for("SS3", date(2026, 4, 9), events) == 2  # not 3
