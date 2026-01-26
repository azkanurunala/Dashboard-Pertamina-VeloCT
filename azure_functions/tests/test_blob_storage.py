"""
Unit tests for Azure Blob Storage integration.
"""

import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json
import uuid
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.blob_storage import BlobStorageManager
from shared.blob_storage_integration import BlobStorageIntegration
from shared.models import NewsArticle, ExecutionResult
from shared.interfaces import ConfigurationError


class TestBlobStorageManager(unittest.TestCase):
    """Unit tests for BlobStorageManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.connection_string = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=testkey123==;EndpointSuffix=core.windows.net"
        self.blob_manager = BlobStorageManager(connection_string=self.connection_string)
        
        # Sample test data
        self.test_content = "This is test file content for blob storage testing."
        self.test_filename = "test_file.txt"
        self.test_metadata = {"test_key": "test_value", "source": "unit_test"}
    
    @patch('shared.blob_storage.BlobServiceClient')
    async def test_initialize_with_connection_string(self, mock_blob_service):
        """Test initialization with connection string."""
        # Mock the blob service client
        mock_client = AsyncMock()
        mock_blob_service.from_connection_string.return_value = mock_client
        
        # Mock container clients
        mock_container = AsyncMock()
        mock_client.get_container_client.return_value = mock_container
        mock_container.create_container = AsyncMock()
        
        # Initialize the blob manager
        await self.blob_manager.initialize()
        
        # Verify initialization
        mock_blob_service.from_connection_string.assert_called_once_with(self.connection_string)
        self.assertIsNotNone(self.blob_manager._client)
        self.assertEqual(len(self.blob_manager._containers), 3)  # temp, processing, archive
    
    @patch('shared.blob_storage.BlobServiceClient')
    async def test_initialize_without_credentials_raises_error(self, mock_blob_service):
        """Test that initialization without credentials raises ConfigurationError."""
        blob_manager = BlobStorageManager()  # No connection string or account URL
        
        with self.assertRaises(ConfigurationError):
            await blob_manager.initialize()
    
    @patch('shared.blob_storage.BlobServiceClient')
    async def test_upload_temp_file(self, mock_blob_service):
        """Test uploading a temporary file."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_blob_service.from_connection_string.return_value = mock_client
        
        mock_container = AsyncMock()
        mock_blob_client = AsyncMock()
        mock_client.get_container_client.return_value = mock_container
        mock_container.get_blob_client.return_value = mock_blob_client
        mock_container.create_container = AsyncMock()
        mock_blob_client.upload_blob = AsyncMock()
        
        # Initialize and upload
        await self.blob_manager.initialize()
        blob_name = await self.blob_manager.upload_temp_file(
            file_content=self.test_content,
            filename=self.test_filename,
            content_type="text/plain",
            metadata=self.test_metadata
        )
        
        # Verify upload was called
        mock_blob_client.upload_blob.assert_called_once()
        self.assertIsInstance(blob_name, str)
        self.assertIn(self.test_filename, blob_name)
    
    @patch('shared.blob_storage.BlobServiceClient')
    async def test_download_file(self, mock_blob_service):
        """Test downloading a file."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_blob_service.from_connection_string.return_value = mock_client
        
        mock_container = AsyncMock()
        mock_blob_client = AsyncMock()
        mock_download_stream = AsyncMock()
        
        mock_client.get_container_client.return_value = mock_container
        mock_container.get_blob_client.return_value = mock_blob_client
        mock_container.create_container = AsyncMock()
        mock_blob_client.download_blob.return_value = mock_download_stream
        mock_download_stream.readall.return_value = self.test_content.encode('utf-8')
        
        # Initialize and download
        await self.blob_manager.initialize()
        content = await self.blob_manager.download_file("test_blob.txt")
        
        # Verify download
        mock_blob_client.download_blob.assert_called_once()
        self.assertEqual(content, self.test_content.encode('utf-8'))
    
    @patch('shared.blob_storage.BlobServiceClient')
    async def test_delete_file(self, mock_blob_service):
        """Test deleting a file."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_blob_service.from_connection_string.return_value = mock_client
        
        mock_container = AsyncMock()
        mock_blob_client = AsyncMock()
        mock_client.get_container_client.return_value = mock_container
        mock_container.get_blob_client.return_value = mock_blob_client
        mock_container.create_container = AsyncMock()
        mock_blob_client.delete_blob = AsyncMock()
        
        # Initialize and delete
        await self.blob_manager.initialize()
        result = await self.blob_manager.delete_file("test_blob.txt")
        
        # Verify deletion
        mock_blob_client.delete_blob.assert_called_once()
        self.assertTrue(result)
    
    @patch('shared.blob_storage.BlobServiceClient')
    async def test_delete_nonexistent_file_returns_false(self, mock_blob_service):
        """Test deleting a non-existent file returns False."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_blob_service.from_connection_string.return_value = mock_client
        
        mock_container = AsyncMock()
        mock_blob_client = AsyncMock()
        mock_client.get_container_client.return_value = mock_container
        mock_container.get_blob_client.return_value = mock_blob_client
        mock_container.create_container = AsyncMock()
        mock_blob_client.delete_blob.side_effect = Exception("Blob not found")
        
        # Initialize and attempt delete
        await self.blob_manager.initialize()
        result = await self.blob_manager.delete_file("nonexistent_blob.txt")
        
        # Verify result
        self.assertFalse(result)
    
    @patch('shared.blob_storage.BlobServiceClient')
    async def test_list_files(self, mock_blob_service):
        """Test listing files in a container."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_blob_service.from_connection_string.return_value = mock_client
        
        mock_container = AsyncMock()
        mock_client.get_container_client.return_value = mock_container
        mock_container.create_container = AsyncMock()
        
        # Mock blob list
        mock_blob1 = Mock()
        mock_blob1.name = "file1.txt"
        mock_blob1.size = 1024
        mock_blob1.last_modified = datetime.now()
        mock_blob1.content_settings = Mock()
        mock_blob1.content_settings.content_type = "text/plain"
        mock_blob1.metadata = {"test": "value"}
        
        mock_blob2 = Mock()
        mock_blob2.name = "file2.txt"
        mock_blob2.size = 2048
        mock_blob2.last_modified = datetime.now()
        mock_blob2.content_settings = None
        mock_blob2.metadata = None
        
        async def mock_list_blobs(*args, **kwargs):
            for blob in [mock_blob1, mock_blob2]:
                yield blob
        
        mock_container.list_blobs = mock_list_blobs
        
        # Initialize and list files
        await self.blob_manager.initialize()
        files = await self.blob_manager.list_files(include_metadata=True)
        
        # Verify results
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0]["name"], "file1.txt")
        self.assertEqual(files[0]["size"], 1024)
        self.assertEqual(files[0]["metadata"], {"test": "value"})
        self.assertEqual(files[1]["name"], "file2.txt")
        self.assertIsNone(files[1]["content_type"])
    
    @patch('shared.blob_storage.BlobServiceClient')
    async def test_cleanup_expired_files(self, mock_blob_service):
        """Test cleanup of expired files."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_blob_service.from_connection_string.return_value = mock_client
        
        mock_container = AsyncMock()
        mock_blob_client = AsyncMock()
        mock_client.get_container_client.return_value = mock_container
        mock_container.get_blob_client.return_value = mock_blob_client
        mock_container.create_container = AsyncMock()
        mock_blob_client.delete_blob = AsyncMock()
        
        # Mock expired blob
        mock_blob = Mock()
        mock_blob.name = "expired_file.txt"
        mock_blob.metadata = {
            "expires_at": (datetime.now() - timedelta(hours=1)).isoformat()  # Expired 1 hour ago
        }
        
        async def mock_list_blobs(*args, **kwargs):
            yield mock_blob
        
        mock_container.list_blobs = mock_list_blobs
        
        # Initialize and cleanup
        await self.blob_manager.initialize()
        result = await self.blob_manager.cleanup_expired_files()
        
        # Verify cleanup
        self.assertTrue(result.success)
        self.assertIn("1 files deleted", result.message)
        mock_blob_client.delete_blob.assert_called_once()


class TestBlobStorageIntegration(unittest.TestCase):
    """Unit tests for BlobStorageIntegration class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.integration = BlobStorageIntegration()
        
        # Sample test data
        self.sample_articles = [
            NewsArticle(
                id=str(uuid.uuid4()),
                title="Test Article 1",
                content="This is test content for article 1.",
                url="https://example.com/article1",
                source="test_source",
                published_date=datetime.now(),
                scraped_date=datetime.now(),
                keywords=["test", "article"],
                language="en"
            ),
            NewsArticle(
                id=str(uuid.uuid4()),
                title="Test Article 2",
                content="This is test content for article 2.",
                url="https://example.com/article2",
                source="test_source",
                published_date=datetime.now(),
                scraped_date=datetime.now(),
                keywords=["test", "news"],
                language="en"
            )
        ]
        
        self.execution_id = str(uuid.uuid4())
        self.source_name = "test_source"
    
    @patch('shared.blob_storage_integration.create_blob_storage_manager')
    @patch('shared.blob_storage_integration.config_manager')
    async def test_initialize(self, mock_config_manager, mock_create_manager):
        """Test initialization of blob storage integration."""
        # Setup mocks
        mock_config_manager.get_blob_storage_config.return_value = {
            "connection_string": "test_connection_string",
            "account_url": None
        }
        
        mock_blob_manager = AsyncMock()
        mock_create_manager.return_value = mock_blob_manager
        
        # Initialize
        await self.integration.initialize()
        
        # Verify initialization
        mock_config_manager.get_blob_storage_config.assert_called_once()
        mock_create_manager.assert_called_once_with(
            connection_string="test_connection_string",
            account_url=None
        )
        self.assertTrue(self.integration._initialized)
    
    @patch('shared.blob_storage_integration.create_blob_storage_manager')
    @patch('shared.blob_storage_integration.config_manager')
    async def test_store_scraped_data_temporarily(self, mock_config_manager, mock_create_manager):
        """Test storing scraped data temporarily."""
        # Setup mocks
        mock_config_manager.get_blob_storage_config.return_value = {
            "connection_string": "test_connection_string",
            "account_url": None
        }
        
        mock_blob_manager = AsyncMock()
        mock_blob_manager.upload_temp_file.return_value = "test_blob_name.json"
        mock_create_manager.return_value = mock_blob_manager
        
        # Store data
        blob_name = await self.integration.store_scraped_data_temporarily(
            articles=self.sample_articles,
            source_name=self.source_name,
            execution_id=self.execution_id
        )
        
        # Verify storage
        mock_blob_manager.upload_temp_file.assert_called_once()
        self.assertEqual(blob_name, "test_blob_name.json")
        
        # Verify call arguments
        call_args = mock_blob_manager.upload_temp_file.call_args
        self.assertIn("scraped_data_test_source", call_args.kwargs["filename"])
        self.assertEqual(call_args.kwargs["content_type"], "application/json")
        self.assertEqual(call_args.kwargs["metadata"]["source"], self.source_name)
    
    @patch('shared.blob_storage_integration.create_blob_storage_manager')
    @patch('shared.blob_storage_integration.config_manager')
    async def test_retrieve_scraped_data(self, mock_config_manager, mock_create_manager):
        """Test retrieving scraped data."""
        # Setup mocks
        mock_config_manager.get_blob_storage_config.return_value = {
            "connection_string": "test_connection_string",
            "account_url": None
        }
        
        test_data = {
            "source": self.source_name,
            "execution_id": self.execution_id,
            "article_count": 2,
            "articles": [article.__dict__ for article in self.sample_articles]
        }
        
        mock_blob_manager = AsyncMock()
        mock_blob_manager.download_file.return_value = json.dumps(test_data).encode('utf-8')
        mock_create_manager.return_value = mock_blob_manager
        
        # Retrieve data
        retrieved_data = await self.integration.retrieve_scraped_data("test_blob.json")
        
        # Verify retrieval
        mock_blob_manager.download_file.assert_called_once_with("test_blob.json")
        self.assertEqual(retrieved_data["source"], self.source_name)
        self.assertEqual(retrieved_data["article_count"], 2)
    
    @patch('shared.blob_storage_integration.create_blob_storage_manager')
    @patch('shared.blob_storage_integration.config_manager')
    async def test_create_temporary_workspace(self, mock_config_manager, mock_create_manager):
        """Test creating a temporary workspace."""
        # Setup mocks
        mock_config_manager.get_blob_storage_config.return_value = {
            "connection_string": "test_connection_string",
            "account_url": None
        }
        
        mock_blob_manager = AsyncMock()
        mock_blob_manager.upload_temp_file.return_value = f"workspace_{self.execution_id}/workspace_info.json"
        mock_create_manager.return_value = mock_blob_manager
        
        # Create workspace
        workspace_prefix = await self.integration.create_temporary_workspace(self.execution_id)
        
        # Verify workspace creation
        mock_blob_manager.upload_temp_file.assert_called_once()
        self.assertEqual(workspace_prefix, f"workspace_{self.execution_id}")
        
        # Verify metadata file creation
        call_args = mock_blob_manager.upload_temp_file.call_args
        self.assertIn("workspace_info.json", call_args.kwargs["filename"])
        self.assertEqual(call_args.kwargs["content_type"], "application/json")


def run_async_test(coro):
    """Helper function to run async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Convert async test methods to sync for unittest
def make_sync_test(async_method):
    """Convert async test method to sync."""
    def sync_method(self):
        return run_async_test(async_method(self))
    return sync_method


# Apply sync conversion to all async test methods
for cls in [TestBlobStorageManager, TestBlobStorageIntegration]:
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if attr_name.startswith('test_') and asyncio.iscoroutinefunction(attr):
            setattr(cls, attr_name, make_sync_test(attr))


if __name__ == '__main__':
    unittest.main()