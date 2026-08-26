import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock

from crowd_predictions.etl.crowd.extract import CrowdExtract
from crowd_predictions.etl.crowd.transform import CrowdTransform
from crowd_predictions.helpers import uploader


def test_extract_synthetic_respects_enable_flags():
    """ENABLE_SMARTSPOT/ENABLE_LIDAR set to false must empty that source, without
    touching the other one - it is the segregation that allows a Smart-Spot-only
    on-premise deployment."""
    with patch.dict(os.environ, {"ENABLE_LIDAR": "false", "DATA_SOURCE": "synthetic", "SYNTHETIC_DAYS": "2"}):
        extractor = CrowdExtract()
        assert extractor.extract() is True
        assert len(extractor.smartspot_counts) > 0
        assert extractor.lidar_zone_counts == {}

    with patch.dict(os.environ, {"ENABLE_SMARTSPOT": "false", "DATA_SOURCE": "synthetic"}):
        extractor = CrowdExtract()
        assert extractor.extract() is True
        assert extractor.smartspot_counts == {}


def test_extract_real_lidar_reads_from_the_broker():
    """DATA_SOURCE=real, LIDAR side: helpers/lidar_zone_history.py, not the old
    always-empty stub."""
    entities = [
        {"id": "urn:ngsi-ld:CrowdFlowLidarZone:Z01", "type": "CrowdFlowLidarZone",
         "totalConcurrentMax": 9},
    ]
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = entities
    response.raise_for_status.return_value = None

    env = {"ENABLE_SMARTSPOT": "false", "ENABLE_LIDAR": "true", "DATA_SOURCE": "real",
           "AETHER_LINK_URL": "https://aether.example", "FIWARE_TENANT": "demo_tenant"}
    with patch.dict(os.environ, env), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=response):
        extractor = CrowdExtract()
        assert extractor.extract() is True
    assert extractor.lidar_zone_counts == {"Z01": 9}


def test_extract_unknown_data_source_raises():
    with patch.dict(os.environ, {"DATA_SOURCE": "not_a_real_source"}):
        extractor = CrowdExtract()
        try:
            extractor.extract()
            assert False, "should have raised ValueError"
        except ValueError:
            pass


def test_transform_exports_one_csv_per_zone_with_crowdflowzone_shape():
    tmp_dir = tempfile.mkdtemp()
    try:
        with patch.dict(os.environ, {"DATA_SOURCE": "synthetic", "SYNTHETIC_DAYS": "3"}):
            extractor = CrowdExtract()
            extractor.extract()

        transformer = CrowdTransform(extractor.smartspot_counts, extractor.lidar_zone_counts, output_dir=tmp_dir)
        assert transformer.transform() is True
        assert len(transformer.exported_files) == len(transformer.zone_totals)
        assert len(transformer.exported_files) > 0

        import pandas as pd
        sample = pd.read_csv(transformer.exported_files[0])
        assert list(sample.columns) == [
            "urn", "type", "name", "timestamp", "occupancy",
            "confidence", "case", "smartspotSignal",
            "smartspotDeltaPct", "latitude", "longitude",
            "lidarSerial", "smartspotSerial",
        ]
        assert sample["type"].iloc[0] == "CrowdFlowZone"
        assert sample["urn"].iloc[0].startswith("urn:ngsi-ld:CrowdFlowZone:")
        assert -90 <= sample["latitude"].iloc[0] <= 90
        assert -180 <= sample["longitude"].iloc[0] <= 180
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_uploader_entity_type_extracted_from_urn_and_queue_called_correctly():
    """The contract that replicates EntityController::uploadDataToEntity: a fixed task
    'platform.data.importation_job', params with urn/type/tenant/scope/storage_file_path."""
    tmp_dir = tempfile.mkdtemp()
    try:
        csv_path = os.path.join(tmp_dir, "urn:ngsi-ld:CrowdFlowZone:Z01.csv")
        with open(csv_path, "w") as f:
            f.write("urn,type\nurn:ngsi-ld:CrowdFlowZone:Z01,CrowdFlowZone\n")

        fake_storage = MagicMock()
        fake_response = MagicMock(status_code=202, text="")

        with patch.dict(os.environ, {"QUEUES_CONSUMER_API_URL": "https://fake-queues.local",
                                      "QUEUES_CONSUMER_USER_ID": "7",
                                      "FIWARE_TENANT": "libelium", "FIWARE_SCOPE": "tenant_a"}):
            with patch.object(uploader, "get_storage", return_value=fake_storage):
                with patch("crowd_predictions.helpers.uploader.requests.post", return_value=fake_response) as mock_post:
                    ok = uploader.upload_csv_via_s3_and_queue(csv_path, "urn:ngsi-ld:CrowdFlowZone:Z01")

        assert ok is True
        fake_storage.upload_file.assert_called_once()
        mock_post.assert_called_once()
        call_url, call_kwargs = mock_post.call_args[0][0], mock_post.call_args[1]
        assert call_url == "https://fake-queues.local/publish"
        body = call_kwargs["json"]
        assert body["task"] == "platform.data.importation_job"
        assert body["params"]["urn"] == "urn:ngsi-ld:CrowdFlowZone:Z01"
        assert body["params"]["type"] == "CrowdFlowZone"
        assert body["params"]["tenant"] == "libelium"
        assert body["params"]["scope"] == "tenant_a"
        # Whoever the consumer attributes the job to and notifies - no longer a
        # hardcoded 1.
        assert body["params"]["user_id"] == 7
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_uploader_returns_false_without_queue_url(tmp_path):
    """The CSV has to EXIST: with a made-up path this returned False at
    `csv_path.exists()` without ever reaching the guard, and passed with the guard
    deleted."""
    csv = tmp_path / "urn:ngsi-ld:CrowdFlowZone:Z01.csv"
    csv.write_text("urn,type,timestamp\nurn:ngsi-ld:CrowdFlowZone:Z01,CrowdFlowZone,2026-01-01\n")

    with patch.dict(os.environ, {"QUEUES_CONSUMER_USER_ID": "7", "FIWARE_TENANT": "t"}):
        os.environ.pop("QUEUES_CONSUMER_API_URL", None)
        ok = uploader.upload_csv_via_s3_and_queue(str(csv), "urn:ngsi-ld:CrowdFlowZone:Z01")
    assert ok is False


def test_the_three_mandatory_csv_columns_come_from_one_place():
    """A typo in urn/type/timestamp is NOT rejected by the importation job: it lands
    as a different attribute and the entity gets a property nobody reads. The three
    producers share the names so they cannot drift apart."""
    from crowd_predictions.helpers.uploader import (CSV_MANDATORY_COLUMNS, TIMESTAMP_COLUMN,
                                                     TYPE_COLUMN, URN_COLUMN)
    from crowd_predictions.fake_measures import CSV_LEADING_COLUMNS

    # Against the LITERAL, not against the tuple they are unpacked from: comparing
    # (URN_COLUMN, ...) with CSV_MANDATORY_COLUMNS cannot fail by construction, and a
    # typo like "tiemstamp" went through it unnoticed.
    assert CSV_MANDATORY_COLUMNS == ("urn", "type", "timestamp")
    assert (URN_COLUMN, TYPE_COLUMN, TIMESTAMP_COLUMN) == ("urn", "type", "timestamp")
    assert CSV_LEADING_COLUMNS is CSV_MANDATORY_COLUMNS, "fake_measures must not redefine them"


def test_the_published_column_order_is_unchanged():
    """Guards the wire format while the names got centralized: whether the consumer's
    parser reads by name or by position is not verified, so the order must not move."""
    import pandas as pd

    tmp_dir = tempfile.mkdtemp()
    try:
        with patch.dict(os.environ, {"DATA_SOURCE": "synthetic", "SYNTHETIC_DAYS": "1"}):
            extractor = CrowdExtract()
            extractor.extract()
        transformer = CrowdTransform(extractor.smartspot_counts, extractor.lidar_zone_counts,
                                      output_dir=tmp_dir)
        assert transformer.transform() is True

        columns = list(pd.read_csv(transformer.exported_files[0]).columns)
        assert columns[:4] == ["urn", "type", "name", "timestamp"]
    finally:
        shutil.rmtree(tmp_dir)


def test_zone_rows_carry_the_device_serials_as_json_arrays():
    """lidarSerial/smartspotSerial let a dashboard join the zone entity with the
    per-device ones without reading zones.json. SERIALS, so the consumer appends
    whichever datamodel suffix it needs - the Smart Spot entity suffix is stripped."""
    import json as _json
    import tempfile as _tempfile, shutil as _shutil
    from crowd_predictions.zones_config import ZONES
    from crowd_predictions.etl.crowd.transform import SMARTSPOT_ENTITY_SUFFIX, _serial

    tmp_dir = _tempfile.mkdtemp()
    try:
        with patch.dict(os.environ, {"DATA_SOURCE": "synthetic", "SYNTHETIC_DAYS": "1"}):
            extractor = CrowdExtract()
            extractor.extract()
        transformer = CrowdTransform(extractor.smartspot_counts, extractor.lidar_zone_counts,
                                     output_dir=tmp_dir)
        assert transformer.transform() is True

        import pandas as pd
        sample = pd.read_csv(transformer.exported_files[0])
        zone_id = sample["urn"].iloc[0].rsplit(":", 1)[-1]
        zone = ZONES[zone_id]
        assert _json.loads(sample["lidarSerial"].iloc[0]) == zone.lidar_ids
        published = _json.loads(sample["smartspotSerial"].iloc[0])
        assert published == [_serial(d) for d in zone.smartspot_ids]
        assert not any(s.endswith(SMARTSPOT_ENTITY_SUFFIX) for s in published)
    finally:
        _shutil.rmtree(tmp_dir, ignore_errors=True)


def test_the_smartspot_suffix_is_stripped_only_when_present():
    """zones.json declares the full entity id (that is what the reader matches);
    an id without the suffix is published unchanged, not truncated."""
    from crowd_predictions.etl.crowd.transform import _serial

    assert _serial("SPT0123_CFO") == "SPT0123"
    assert _serial("SPT0123") == "SPT0123"
    assert _serial("SS5") == "SS5"
