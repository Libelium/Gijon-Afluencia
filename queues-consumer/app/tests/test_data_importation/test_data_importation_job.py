import os
from unittest.mock import MagicMock, Mock, patch, call
import pytest
from jobs.data.data_importation.data_importation_job import DataImportationJob
from schemas.data_importation_request import DataImportationRequest
from schemas.entity_data_notification import (
    EntityAttr,
    EntityAttrType,
    EntityDataNotification,
)


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    return MagicMock()


@pytest.fixture
def mock_realtime_db_session():
    """Mock realtime database session"""
    return MagicMock()


@pytest.fixture
def sample_request():
    """Sample DataImportationRequest for testing"""
    return DataImportationRequest(
        user_id=1,
        tenant="pid",
        scope="/",
        storage_file_path="data/test_file.csv",
    )


@pytest.fixture
def sample_notifications():
    """Sample notifications that would be returned by parser"""
    return [
        EntityDataNotification(
            urn="urn:ngsi-ld:Device:001",
            tenant="pid",
            scope="/",
            type="TestDevice",
            notified_at=None,
            data=[
                EntityAttr(
                    name="temperature",
                    value=25.5,
                    timestamp=1750258530.0,
                    type=EntityAttrType.PROPERTY,
                ),
                EntityAttr(
                    name="humidity",
                    value=60,
                    timestamp=1750258530.0,
                    type=EntityAttrType.PROPERTY,
                ),
            ],
        )
    ]


@pytest.fixture
def mock_entity():
    """Mock entity returned from database"""
    entity = MagicMock()
    entity.id = 123
    entity.datamodel = "TestDevice"
    return entity




class TestDataImportationJobInitialization:
    """Tests for DataImportationJob initialization"""

    @patch("jobs.data.data_importation.data_importation_job.storage")
    @patch("jobs.data.data_importation.data_importation_job.ParserFactory")
    def test_initialization_with_csv_file(
        self, mock_parser_factory, mock_storage, sample_request, mock_db_session, mock_realtime_db_session
    ):
        """Test job initializes correctly with CSV file"""
        from jobs.data.data_importation.data_importation_job import DataImportationJob

        mock_parser = MagicMock()
        mock_parser_factory.return_value.get_parser.return_value = mock_parser

        job = DataImportationJob(sample_request, mock_db_session, mock_realtime_db_session)

        assert job.request == sample_request
        # Sessions are now bound during handle(), not __init__. The injected
        # values are stored under _injected_* and assigned to .main_db /
        # .realtime_db only when handle() runs.
        assert job._injected_main == mock_db_session
        assert job._injected_realtime == mock_realtime_db_session
        assert job.parser == mock_parser
        mock_parser_factory.return_value.get_parser.assert_called_once_with("csv")

    @patch("jobs.data.data_importation.data_importation_job.storage")
    @patch("jobs.data.data_importation.data_importation_job.ParserFactory")
    def test_initialization_extracts_file_extension(
        self, mock_parser_factory, mock_storage, mock_db_session, mock_realtime_db_session
    ):
        """Test job correctly extracts file extension from path"""
        from jobs.data.data_importation.data_importation_job import DataImportationJob

        mock_parser = MagicMock()
        mock_parser_factory.return_value.get_parser.return_value = mock_parser

        request = DataImportationRequest(
            user_id=1,
            storage_file_path="folder/subfolder/data.xlsx",
        )

        DataImportationJob(request, mock_db_session, mock_realtime_db_session)

        mock_parser_factory.return_value.get_parser.assert_called_once_with("xlsx")


class TestDataImportationJobHandle:
    """Tests for the main handle() workflow"""

    @patch("jobs.data.data_importation.data_importation_job.storage")
    @patch("jobs.data.data_importation.data_importation_job.ParserFactory")
    def test_handle_success_workflow(
        self,
        mock_parser_factory,
        mock_storage,
        sample_request,
        sample_notifications,
        mock_db_session,
        mock_realtime_db_session,
    ):
        """Test complete successful workflow through handle()"""
        from jobs.data.data_importation.data_importation_job import DataImportationJob

        # Setup mocks
        mock_parser = MagicMock()
        mock_parser.parse.return_value = sample_notifications
        mock_parser_factory.return_value.get_parser.return_value = mock_parser

        job = DataImportationJob(sample_request, mock_db_session, mock_realtime_db_session)

        # Mock the private methods
        with patch.object(job, '_download_file_from_storage', return_value='/tmp/test.csv'), \
             patch.object(job, '_parse_file', return_value=sample_notifications), \
             patch.object(job, '_process_notifications'), \
             patch.object(job, '_cleanup'):

            job.handle()

            # Verify all steps were called
            job._download_file_from_storage.assert_called_once()
            job._parse_file.assert_called_once_with('/tmp/test.csv')
            job._process_notifications.assert_called_once_with(sample_notifications)
            job._cleanup.assert_called_once_with('/tmp/test.csv')

    @patch("jobs.data.data_importation.data_importation_job.ParserFactory")
    def test_handle_raises_on_download_error(
        self, mock_parser_factory,  sample_request, mock_db_session, mock_realtime_db_session
    ):
        """Test handle() propagates download errors"""
        mock_parser = MagicMock()
        mock_parser_factory.return_value.get_parser.return_value = mock_parser

        job = DataImportationJob(sample_request, mock_db_session, mock_realtime_db_session)

        with patch.object(job, '_download_file_from_storage', side_effect=Exception("Download failed")):
            with pytest.raises(Exception, match="Download failed"):
                job.handle()

    @patch("jobs.data.data_importation.data_importation_job.ParserFactory")
    def test_handle_raises_on_parse_error(
        self, mock_parser_factory,  sample_request, mock_db_session, mock_realtime_db_session
    ):
        """Test handle() propagates parse errors"""
        mock_parser = MagicMock()
        mock_parser_factory.return_value.get_parser.return_value = mock_parser

        job = DataImportationJob(sample_request, mock_db_session, mock_realtime_db_session)

        with patch.object(job, '_download_file_from_storage', return_value='/tmp/test.csv'), \
             patch.object(job, '_parse_file', side_effect=ValueError("Parse failed")):
            with pytest.raises(ValueError, match="Parse failed"):
                job.handle()


class TestDownloadFileFromStorage:
    """Tests for _download_file_from_storage method"""

    @patch("jobs.data.data_importation.data_importation_job.ParserFactory")
    @patch("jobs.data.data_importation.data_importation_job.storage")
    def test_download_file_success(
        self,
        mock_storage,
        mock_parser_factory,
        
        sample_request,
        mock_db_session,
        mock_realtime_db_session,
    ):
        """Test successful file download from storage"""
        mock_parser = MagicMock()
        mock_parser_factory.return_value.get_parser.return_value = mock_parser
        mock_storage.download_file.return_value = "/tmp/test_file.csv"

        job = DataImportationJob(sample_request, mock_db_session, mock_realtime_db_session)
        local_path = job._download_file_from_storage()

        assert local_path == "/tmp/test_file.csv"
        mock_storage.download_file.assert_called_once_with(
            "test_file.csv", "data/test_file.csv"
        )

    @patch("jobs.data.data_importation.data_importation_job.ParserFactory")
    @patch("jobs.data.data_importation.data_importation_job.storage")
    def test_download_file_handles_storage_error(
        self,
        mock_storage,
        mock_parser_factory,
        
        sample_request,
        mock_db_session,
        mock_realtime_db_session,
    ):
        """Test error handling when storage download fails"""
        mock_parser = MagicMock()
        mock_parser_factory.return_value.get_parser.return_value = mock_parser
        mock_storage.download_file.side_effect = Exception("Storage error")

        job = DataImportationJob(sample_request, mock_db_session, mock_realtime_db_session)

        with pytest.raises(Exception, match="Storage error"):
            job._download_file_from_storage()


class TestParseFile:
    """Tests for _parse_file method"""

    @patch("jobs.data.data_importation.data_importation_job.ParserFactory")
    def test_parse_file_success(
        self,
        mock_parser_factory,
        
        sample_request,
        sample_notifications,
        mock_db_session,
        mock_realtime_db_session,
    ):
        """Test successful file parsing"""
        mock_parser = MagicMock()
        mock_parser.parse.return_value = sample_notifications
        mock_parser_factory.return_value.get_parser.return_value = mock_parser

        job = DataImportationJob(sample_request, mock_db_session, mock_realtime_db_session)
        notifications = job._parse_file("/tmp/test.csv")

        assert notifications == sample_notifications
        mock_parser.parse.assert_called_once_with("/tmp/test.csv", sample_request)

    @patch("jobs.data.data_importation.data_importation_job.ParserFactory")
    def test_parse_file_handles_parse_error(
        self, mock_parser_factory,  sample_request, mock_db_session, mock_realtime_db_session
    ):
        """Test error handling when parsing fails"""
        mock_parser = MagicMock()
        mock_parser.parse.side_effect = ValueError("Invalid format")
        mock_parser_factory.return_value.get_parser.return_value = mock_parser

        job = DataImportationJob(sample_request, mock_db_session, mock_realtime_db_session)

        with pytest.raises(ValueError, match="Invalid format"):
            job._parse_file("/tmp/test.csv")




class TestCleanup:
    """Tests for _cleanup method"""

    @patch("jobs.data.data_importation.data_importation_job.ParserFactory")
    @patch("jobs.data.data_importation.data_importation_job.storage")
    @patch("jobs.data.data_importation.data_importation_job.os.path.exists")
    @patch("jobs.data.data_importation.data_importation_job.os.remove")
    def test_cleanup_removes_local_and_storage_files(
        self,
        mock_remove,
        mock_exists,
        mock_storage,
        mock_parser_factory,
        
        sample_request,
        mock_db_session,
        mock_realtime_db_session,
    ):
        """Test cleanup removes both local and storage files"""
        mock_parser = MagicMock()
        mock_parser_factory.return_value.get_parser.return_value = mock_parser
        mock_exists.return_value = True

        job = DataImportationJob(sample_request, mock_db_session, mock_realtime_db_session)
        job._cleanup("/tmp/test.csv")

        # Verify local file was removed
        mock_remove.assert_called_once_with("/tmp/test.csv")

        # Verify storage file was deleted
        mock_storage.delete_file.assert_called_once_with("data/test_file.csv")

    @patch("jobs.data.data_importation.data_importation_job.ParserFactory")
    @patch("jobs.data.data_importation.data_importation_job.storage")
    @patch("jobs.data.data_importation.data_importation_job.os.path.exists")
    def test_cleanup_handles_nonexistent_file(
        self,
        mock_exists,
        mock_storage,
        mock_parser_factory,
        
        sample_request,
        mock_db_session,
        mock_realtime_db_session,
    ):
        """Test cleanup handles case when local file doesn't exist"""
        mock_parser = MagicMock()
        mock_parser_factory.return_value.get_parser.return_value = mock_parser
        mock_exists.return_value = False

        job = DataImportationJob(sample_request, mock_db_session, mock_realtime_db_session)

        with patch("jobs.data.data_importation.data_importation_job.os.remove") as mock_remove:
            job._cleanup("/tmp/test.csv")

            # Verify remove was not called for non-existent file
            mock_remove.assert_not_called()

            # Verify storage file deletion was still attempted
            mock_storage.delete_file.assert_called_once_with("data/test_file.csv")

    @patch("jobs.data.data_importation.data_importation_job.ParserFactory")
    @patch("jobs.data.data_importation.data_importation_job.storage")
    @patch("jobs.data.data_importation.data_importation_job.os.path.exists")
    @patch("jobs.data.data_importation.data_importation_job.os.remove")
    def test_cleanup_handles_removal_error(
        self,
        mock_remove,
        mock_exists,
        mock_storage,
        mock_parser_factory,
        
        sample_request,
        mock_db_session,
        mock_realtime_db_session,
    ):
        """Test cleanup handles errors gracefully without raising"""
        mock_parser = MagicMock()
        mock_parser_factory.return_value.get_parser.return_value = mock_parser
        mock_exists.return_value = True
        mock_remove.side_effect = OSError("Permission denied")

        job = DataImportationJob(sample_request, mock_db_session, mock_realtime_db_session)

        # Should not raise exception
        job._cleanup("/tmp/test.csv")

    @patch("jobs.data.data_importation.data_importation_job.ParserFactory")
    @patch("jobs.data.data_importation.data_importation_job.storage")
    @patch("jobs.data.data_importation.data_importation_job.os.path.exists")
    def test_cleanup_handles_none_file_path(
        self,
        mock_exists,
        mock_storage,
        mock_parser_factory,
        
        sample_request,
        mock_db_session,
        mock_realtime_db_session,
    ):
        """Test cleanup handles None file path"""
        mock_parser = MagicMock()
        mock_parser_factory.return_value.get_parser.return_value = mock_parser

        job = DataImportationJob(sample_request, mock_db_session, mock_realtime_db_session)

        with patch("jobs.data.data_importation.data_importation_job.os.remove") as mock_remove:
            job._cleanup(None)

            # Verify file operations were not attempted
            mock_remove.assert_not_called()
            mock_exists.assert_not_called()

            # Storage cleanup should still happen
            mock_storage.delete_file.assert_called_once_with("data/test_file.csv")
