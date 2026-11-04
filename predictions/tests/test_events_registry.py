import os
from datetime import date
from unittest.mock import patch

from crowd_predictions.events_registry import (
    load_events_registry, event_days, events_in_window, fingerprint, list_raw_rows, append_event,
    delete_event_at_index, events_registry_key,
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
    assert events[0]["end_date"] == date(2026, 4, 9)  # no end_date = a one-day event
    assert events[0]["device_ids"] is None  # None = global, not an empty set
    assert events[0]["start_hour"] is None and events[0]["end_hour"] is None


def test_append_then_load_parses_a_scoped_event_device_ids_list(tmp_path):
    storage = _DictStorage()
    with _tenant_scope():
        append_event(storage, "2026-09-02", "small_event", "SS3,SS7,SS11", "Market", local_dir=str(tmp_path))
        events = load_events_registry(storage, local_dir=str(tmp_path))

    assert events[0]["device_ids"] == {"SS3", "SS7", "SS11"}
    assert events[0]["event_type"] == "small_event"


def test_a_week_long_event_with_hours_round_trips(tmp_path):
    storage = _DictStorage()
    with _tenant_scope():
        append_event(storage, "2026-12-14", "market", "", "Christmas market", end_date="2026-12-20",
                     start_hour=10, end_hour=21, local_dir=str(tmp_path))
        events = load_events_registry(storage, local_dir=str(tmp_path))

    assert events[0]["date"] == date(2026, 12, 14)
    assert events[0]["end_date"] == date(2026, 12, 20)
    assert (events[0]["start_hour"], events[0]["end_hour"]) == (10, 21)


def test_appending_to_a_four_column_registry_upgrades_its_header_and_keeps_its_rows(tmp_path):
    storage = _DictStorage()
    _upload_raw_csv(storage, "date,event_type,device_ids,notes\n2026-04-09,concert,,Old row\n")
    with _tenant_scope():
        append_event(storage, "2026-12-14", "market", end_date="2026-12-20", local_dir=str(tmp_path))
        text = storage.files[events_registry_key()].decode("utf-8")
        events = load_events_registry(storage, local_dir=str(tmp_path))

    assert text.splitlines()[0] == "date,event_type,device_ids,notes,end_date,start_hour,end_hour"
    assert [(e["date"], e["end_date"], e["notes"]) for e in events] == [
        (date(2026, 4, 9), date(2026, 4, 9), "Old row"),
        (date(2026, 12, 14), date(2026, 12, 20), ""),
    ]


def test_append_rejects_an_end_date_before_the_date_and_a_bad_hour(tmp_path):
    storage = _DictStorage()
    with _tenant_scope():
        for kwargs in ({"end_date": "2026-12-01"}, {"start_hour": 25}):
            try:
                append_event(storage, "2026-12-14", "market", local_dir=str(tmp_path), **kwargs)
                assert False, f"should have raised ValueError for {kwargs}"
            except ValueError:
                pass
    assert storage.files == {}


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


def test_an_end_date_before_its_date_skips_only_that_row(tmp_path, caplog):
    storage = _DictStorage()
    _upload_raw_csv(storage, (
        "date,event_type,device_ids,notes,end_date\n"
        "2026-12-14,market,,Reversed,2026-12-01\n"
        "2026-04-09,concert,,Fine,\n"
    ))
    with _tenant_scope():
        with caplog.at_level("WARNING"):
            events = load_events_registry(storage, local_dir=str(tmp_path))

    assert [e["notes"] for e in events] == ["Fine"]
    assert "before" in caplog.text


def test_a_bad_hour_only_loses_the_hour_not_the_event(tmp_path, caplog):
    storage = _DictStorage()
    _upload_raw_csv(storage, (
        "date,event_type,device_ids,notes,end_date,start_hour,end_hour\n"
        "2026-12-14,market,,Market,,ten,21\n"
    ))
    with _tenant_scope():
        with caplog.at_level("WARNING"):
            events = load_events_registry(storage, local_dir=str(tmp_path))

    assert (events[0]["start_hour"], events[0]["end_hour"]) == (None, 21)
    assert "start_hour" in caplog.text


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


def _event(day, end=None, zones=None, **extra):
    return {"date": day, "end_date": end or day, "device_ids": zones, "event_type": "market",
            "notes": "", "start_hour": None, "end_hour": None, **extra}


def test_event_days_of_a_global_event_apply_to_any_zone():
    events = [_event(date(2026, 4, 9))]
    assert event_days("SS1", events) == {date(2026, 4, 9)}
    assert event_days("L23", events) == {date(2026, 4, 9)}


def test_event_days_of_a_scoped_event_only_apply_to_the_listed_zones():
    events = [_event(date(2026, 9, 2), zones={"SS3", "SS7", "SS11"})]
    assert event_days("SS3", events) == {date(2026, 9, 2)}
    assert event_days("SS4", events) == set()  # same area, NOT a listed zone


def test_event_days_cover_the_whole_range_and_merge_overlaps():
    events = [_event(date(2026, 12, 14), end=date(2026, 12, 20)),          # the market week
              _event(date(2026, 12, 20), end=date(2026, 12, 21), zones={"A"})]  # + a concert
    assert event_days("A", events) == {date(2026, 12, d) for d in range(14, 22)}
    assert event_days("B", events) == {date(2026, 12, d) for d in range(14, 21)}


def test_device_ids_is_the_ngsi_ld_urn_not_the_short_ss_code(tmp_path):
    """zone_id in training_data.py comes from Aether's entity "id" (see
    helpers/aether_history.py::resolve_zone_ids) - already a URN, not the
    "SS1"-style shorthand zones_config.py uses for the synthetic fixtures. The
    registry has to be written in that same identifier space to ever match."""
    urn = "urn:ngsi-ld:CrowdFlowZone:P13"
    storage = _DictStorage()
    with _tenant_scope():
        append_event(storage, "2026-04-09", "concert", urn, "Concert", local_dir=str(tmp_path))
        events = load_events_registry(storage, local_dir=str(tmp_path))

    assert events[0]["device_ids"] == {urn}
    assert event_days(urn, events) == {date(2026, 4, 9)}
    assert event_days("P13", events) == set()  # the short code is NOT the URN


def test_events_in_window_keeps_the_zone_events_touching_those_days_in_order():
    market = _event(date(2026, 12, 14), end=date(2026, 12, 20))
    concert = _event(date(2026, 12, 13), zones={"A"})
    elsewhere = _event(date(2026, 12, 15), zones={"B"})
    later = _event(date(2026, 12, 25))
    events = [later, market, elsewhere, concert]

    assert events_in_window("A", date(2026, 12, 13), date(2026, 12, 14), events) == [concert, market]
    assert events_in_window("A", date(2026, 12, 20), date(2026, 12, 21), events) == [market]
    assert events_in_window("A", date(2026, 12, 22), date(2026, 12, 23), events) == []


def test_fingerprint_follows_days_and_zones_not_type_notes_or_hours():
    base = [_event(date(2026, 12, 14), end=date(2026, 12, 20), zones={"A"})]
    same_rows = [_event(date(2026, 12, 14), end=date(2026, 12, 20), zones={"A"},
                        event_type="festival", notes="Renamed", start_hour=10, end_hour=21)]
    longer = [_event(date(2026, 12, 14), end=date(2026, 12, 21), zones={"A"})]
    other_zone = [_event(date(2026, 12, 14), end=date(2026, 12, 20), zones={"B"})]

    assert fingerprint(base) == fingerprint(same_rows)
    assert fingerprint(base) != fingerprint(longer)
    assert fingerprint(base) != fingerprint(other_zone)


def test_fingerprint_until_only_counts_the_days_already_learned():
    """A model whose data reaches 10 December has not learned the market of the 14th:
    registering, moving or deleting it must not look like a change to that model."""
    trained = [_event(date(2026, 4, 9), zones={"A"})]
    with_future = trained + [_event(date(2026, 12, 14), end=date(2026, 12, 20), zones={"A"})]
    moved_future = trained + [_event(date(2026, 12, 15), end=date(2026, 12, 22), zones={"A"})]
    until = date(2026, 12, 10)

    assert fingerprint(with_future, until=until) == fingerprint(trained, until=until)
    assert fingerprint(moved_future, until=until) == fingerprint(trained, until=until)
    assert fingerprint(with_future) != fingerprint(trained)  # without `until`: the whole registry


def test_fingerprint_until_counts_the_learned_part_of_an_event_that_has_begun():
    begun = [_event(date(2026, 12, 14), end=date(2026, 12, 20), zones={"A"})]
    longer = [_event(date(2026, 12, 14), end=date(2026, 12, 25), zones={"A"})]
    until = date(2026, 12, 16)

    assert fingerprint(begun, until=until) != fingerprint([], until=until)  # the 14th-16th are learned
    assert fingerprint(begun, until=until) == fingerprint(longer, until=until)  # only its future changed
