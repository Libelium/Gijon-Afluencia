"""
Tests of the Minio backend (STORAGE_TYPE=local), with the client mocked - same
pattern as tests/test_s3_storage.py with boto3.

A separate file on purpose: if `config.local_storage` were imported from
test_etl_pipeline.py, that file would start needing `minio` installed in order to
run the ETL tests, which is exactly what the lazy imports of config/config.py
avoid.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

from crowd_predictions.config.local_storage import LocalStorage
from crowd_predictions.config.local_storage_settings import LocalStorageSettings


def _storage_with_mock_client():
    settings = LocalStorageSettings(
        ACCESS_ID="key", SECRET_KEY="secret",
        ENDPOINT="minio.test:9000", BUCKET="test-bucket", SECURE=False,
    )
    with patch("crowd_predictions.config.local_storage.Minio") as mock_minio:
        storage = LocalStorage(settings)
    return storage, mock_minio.return_value


def test_download_file_uses_filename_as_key_and_writes_to_path():
    """
    The the reference prediction ETL bug: it used `path` as the object key and wrote to
    a hardcoded path. The contract is `filename`=key, `path`=local destination, and
    etl/predict/extract.py READS from `path`, ignoring the return value.
    """
    storage, client = _storage_with_mock_client()

    response = MagicMock()
    response.stream.return_value = [b"modelo ", b"entrenado"]
    client.get_object.return_value = response

    dest = os.path.join(tempfile.mkdtemp(), "subdir", "crowd_xgboost_model.json")
    result = storage.download_file("crowd_xgboost_model.json", dest)

    # The key is filename, NOT path
    client.get_object.assert_called_once_with("test-bucket", "crowd_xgboost_model.json")
    # It writes where the caller asked, and the parent directory is created
    assert os.path.exists(dest)
    with open(dest, "rb") as f:
        assert f.read() == b"modelo entrenado"
    assert result == dest
    # The connection is released (otherwise the pool runs out)
    response.close.assert_called_once()
    response.release_conn.assert_called_once()


def test_upload_file_creates_bucket_if_missing():
    storage, client = _storage_with_mock_client()
    client.bucket_exists.return_value = False

    result = storage.upload_file("clave.csv", "/tmp/local.csv")

    client.make_bucket.assert_called_once_with("test-bucket")
    client.fput_object.assert_called_once_with("test-bucket", "clave.csv", "/tmp/local.csv")
    assert result == "/tmp/local.csv"


def test_bucket_is_checked_only_once():
    storage, client = _storage_with_mock_client()
    client.bucket_exists.return_value = True

    storage.upload_file("a.csv", "/tmp/a.csv")
    storage.upload_file("b.csv", "/tmp/b.csv")

    assert client.bucket_exists.call_count == 1


def test_delete_file_uses_the_minio_api_not_boto3():
    """parking called client.Object(...).remove(), which is boto3 API and does not
    exist on the minio client."""
    storage, client = _storage_with_mock_client()

    assert storage.delete_file("clave.csv") is True
    client.remove_object.assert_called_once_with("test-bucket", "clave.csv")
