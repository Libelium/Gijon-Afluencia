import pytest
from unittest.mock import MagicMock, patch

from crowd_predictions.config.s3_storage import S3Storage
from crowd_predictions.config.s3_storage_settings import S3StorageSettings


def _storage_with_mock_bucket():
    """boto3 never really connects - Bucket is replaced by a Mock so that WHICH
    ARGUMENTS upload_file/download_file are called with can be checked, with no
    real AWS credentials."""
    settings = S3StorageSettings(ACCESS_ID="x", SECRET_KEY="x", REGION="eu-south-2", BUCKET="test-bucket")
    with patch("boto3.resource") as mock_resource:
        mock_bucket = MagicMock()
        mock_resource.return_value.Bucket.return_value = mock_bucket
        storage = S3Storage(settings)
    return storage, mock_bucket


def test_download_file_goes_through_the_client_in_boto3_order():
    """Two things at once.

    THE ORDER, a real bug found in review: it called download_file(path, local_path) and
    boto3 wants (Key, Filename), so the caller's local path went in as the S3 key and the
    real destination was ignored. It never failed locally and would have broken the first
    time STORAGE_TYPE=s3 was really used. The client takes (Bucket, Key, Filename).

    THE CLIENT and not the bucket resource: boto3 documents clients as thread-safe and
    resources as not, and the LIDAR compaction downloads a whole hour of dumps from a
    thread pool over this one instance.
    """
    storage, mock_bucket = _storage_with_mock_bucket()
    mock_bucket.name = "test-bucket"

    result = storage.download_file("crowd_xgboost_model.json", "/tmp/crowd_xgboost_model.json")

    mock_bucket.meta.client.download_file.assert_called_once_with(
        "test-bucket", "crowd_xgboost_model.json", "/tmp/crowd_xgboost_model.json"
    )
    mock_bucket.download_file.assert_not_called()
    assert result == "/tmp/crowd_xgboost_model.json"


def test_upload_file_passes_filename_and_key_in_boto3_order():
    storage, mock_bucket = _storage_with_mock_bucket()

    result = storage.upload_file("crowd_xgboost_model.json", "/tmp/crowd_xgboost_model.json")

    mock_bucket.upload_file.assert_called_once_with(
        "/tmp/crowd_xgboost_model.json", "crowd_xgboost_model.json"
    )
    assert result == "/tmp/crowd_xgboost_model.json"


def test_delete_files_uses_one_call_per_thousand_keys():
    """One DELETE per dump was HALF the round trips of a compaction run: a few dozen sensors x 120
    dumps an hour is ~5000 deletes. DeleteObjects takes 1000 at a time."""
    storage, mock_bucket = _storage_with_mock_bucket()
    mock_bucket.delete_objects.return_value = {}

    storage.delete_files([f"ote/incoming/d/{n}.gz" for n in range(2500)])

    assert mock_bucket.delete_objects.call_count == 3          # 1000 + 1000 + 500
    first = mock_bucket.delete_objects.call_args_list[0].kwargs["Delete"]
    assert len(first["Objects"]) == 1000
    assert first["Objects"][0] == {"Key": "ote/incoming/d/0.gz"}


def test_delete_files_raises_when_s3_reports_a_key_it_could_not_delete():
    """Silence here would be a duplicate: the caller has just archived those dumps, so one
    surviving gets compacted again into a second object with the same frames."""
    storage, mock_bucket = _storage_with_mock_bucket()
    mock_bucket.delete_objects.return_value = {
        "Errors": [{"Key": "ote/incoming/d/7.gz", "Code": "AccessDenied"}]}

    with pytest.raises(RuntimeError, match="7.gz"):
        storage.delete_files(["ote/incoming/d/7.gz"])
