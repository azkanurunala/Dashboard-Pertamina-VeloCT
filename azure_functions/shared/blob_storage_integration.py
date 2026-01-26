"""
Integration utilities for Azure Blob Storage with the news scraping system.
"""

import asyncio
import tempfile
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from .blob_storage import BlobStorageManager
from .config import config_manager
from .utils import create_blob_storage_manager
from .models import NewsArticle, ExecutionResult, FunctionStatus
from .interfaces import ConfigurationError

logger = logging.getLogger(__name__)


class BlobStorageIntegration:
    """
    Integration class that provides high-level blob storage operations for the news scraping system.
    """
    
    def __init__(self, blob_manager: Optional[BlobStorageManager] = None):
        """
        Initialize the blob storage integration.
        
        Args:
            blob_manager: Optional pre-initialized blob storage manager
        """
        self._blob_manager = blob_manager
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the blob storage integration."""
        if not self._blob_manager:
            # Get configuration from config manager
            blob_config = config_manager.get_blob_storage_config()
            
            if not blob_config.get("connection_string") and not blob_config.get("account_url"):
                raise ConfigurationError("Blob storage connection string or account URL not configured")
            
            self._blob_manager = await create_blob_storage_manager(
                connection_string=blob_config.get("connection_string"),
                account_url=blob_config.get("account_url")
            )
        
        self._initialized = True
        logger.info("Blob storage integration initialized")
    
    async def store_scraped_data_temporarily(self, 
                                           articles: List[NewsArticle], 
                                           source_name: str,
                                           execution_id: str) -> str:
        """
        Store scraped articles temporarily in blob storage for processing.
        
        Args:
            articles: List of scraped articles
            source_name: Name of the news source
            execution_id: Unique execution identifier
            
        Returns:
            Blob name of the stored file
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Convert articles to JSON format
            from .utils import safe_json_serialize
            articles_data = {
                "source": source_name,
                "execution_id": execution_id,
                "article_count": len(articles),
                "articles": [article.to_dict() if hasattr(article, 'to_dict') else article.__dict__ for article in articles]
            }
            
            json_content = safe_json_serialize(articles_data)
            
            # Create filename
            filename = f"scraped_data_{source_name}_{execution_id}.json"
            
            # Upload to blob storage
            blob_name = await self._blob_manager.upload_temp_file(
                file_content=json_content,
                filename=filename,
                content_type="application/json",
                metadata={
                    "source": source_name,
                    "execution_id": execution_id,
                    "article_count": str(len(articles)),
                    "data_type": "scraped_articles"
                }
            )
            
            logger.info(f"Stored {len(articles)} articles from {source_name} in blob: {blob_name}")
            return blob_name
            
        except Exception as e:
            logger.error(f"Failed to store scraped data temporarily: {str(e)}")
            raise
    
    async def retrieve_scraped_data(self, blob_name: str) -> Dict[str, Any]:
        """
        Retrieve scraped data from blob storage.
        
        Args:
            blob_name: Name of the blob containing the data
            
        Returns:
            Dictionary containing the scraped data
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Download the file
            content = await self._blob_manager.download_file(blob_name)
            
            # Parse JSON content
            from .utils import safe_json_deserialize
            data = safe_json_deserialize(content.decode('utf-8'))
            
            if not data:
                raise ValueError("Failed to parse scraped data from blob storage")
            
            logger.info(f"Retrieved scraped data from blob: {blob_name}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to retrieve scraped data from {blob_name}: {str(e)}")
            raise
    
    async def store_large_excel_file(self, file_path: str, metadata: Optional[Dict[str, str]] = None) -> str:
        """
        Store a large Excel file using streaming upload.
        
        Args:
            file_path: Path to the Excel file
            metadata: Optional metadata for the file
            
        Returns:
            Blob name of the uploaded file
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Create async generator for file chunks
            async def file_chunk_generator():
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        yield chunk
            
            # Upload using streaming
            blob_name = await self._blob_manager.stream_upload(
                data_stream=file_chunk_generator(),
                blob_name=file_path_obj.name,
                container_name=self._blob_manager.processing_container,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                metadata=metadata or {}
            )
            
            logger.info(f"Uploaded large Excel file: {file_path} -> {blob_name}")
            return blob_name
            
        except Exception as e:
            logger.error(f"Failed to store large Excel file {file_path}: {str(e)}")
            raise
    
    async def download_large_file_streaming(self, blob_name: str, local_path: str) -> None:
        """
        Download a large file using streaming to avoid memory issues.
        
        Args:
            blob_name: Name of the blob to download
            local_path: Local path to save the file
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            with open(local_path, 'wb') as f:
                async for chunk in self._blob_manager.stream_download(blob_name):
                    f.write(chunk)
            
            logger.info(f"Downloaded large file: {blob_name} -> {local_path}")
            
        except Exception as e:
            logger.error(f"Failed to download large file {blob_name}: {str(e)}")
            raise
    
    async def create_temporary_workspace(self, execution_id: str) -> str:
        """
        Create a temporary workspace in blob storage for processing operations.
        
        Args:
            execution_id: Unique execution identifier
            
        Returns:
            Workspace prefix for organizing files
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            from .utils import utc_now
            
            # Create workspace metadata file
            workspace_info = {
                "execution_id": execution_id,
                "created_at": utc_now().isoformat(),
                "workspace_type": "temporary_processing"
            }
            
            workspace_prefix = f"workspace_{execution_id}"
            metadata_filename = f"{workspace_prefix}/workspace_info.json"
            
            from .utils import safe_json_serialize
            await self._blob_manager.upload_temp_file(
                file_content=safe_json_serialize(workspace_info),
                filename=metadata_filename,
                content_type="application/json",
                metadata={
                    "workspace_id": execution_id,
                    "file_type": "workspace_metadata"
                }
            )
            
            logger.info(f"Created temporary workspace: {workspace_prefix}")
            return workspace_prefix
            
        except Exception as e:
            logger.error(f"Failed to create temporary workspace: {str(e)}")
            raise
    
    async def cleanup_workspace(self, workspace_prefix: str) -> ExecutionResult:
        """
        Clean up all files in a temporary workspace.
        
        Args:
            workspace_prefix: Workspace prefix to clean up
            
        Returns:
            Execution result with cleanup statistics
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            from .utils import utc_now
            
            # List all files with the workspace prefix
            files = await self._blob_manager.list_files(
                container_name=self._blob_manager.temp_container,
                prefix=workspace_prefix
            )
            
            deleted_count = 0
            error_count = 0
            
            # Delete each file
            for file_info in files:
                try:
                    await self._blob_manager.delete_file(
                        blob_name=file_info["name"],
                        container_name=self._blob_manager.temp_container
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete workspace file {file_info['name']}: {str(e)}")
                    error_count += 1
            
            result = ExecutionResult(
                function_name="cleanup_workspace",
                execution_id=generate_execution_id(),
                status=FunctionStatus.SUCCESS if error_count == 0 else FunctionStatus.FAILED,
                start_time=utc_now(),
                end_time=utc_now(),
                output_summary={
                    "workspace_prefix": workspace_prefix,
                    "deleted_count": deleted_count,
                    "error_count": error_count
                }
            )
            
            logger.info(f"Cleaned up workspace {workspace_prefix}: {deleted_count} files deleted")
            return result
            
        except Exception as e:
            logger.error(f"Failed to cleanup workspace {workspace_prefix}: {str(e)}")
            return ExecutionResult(
                function_name="cleanup_workspace",
                execution_id=generate_execution_id(),
                status=FunctionStatus.FAILED,
                start_time=utc_now(),
                end_time=utc_now(),
                error_message=str(e),
                output_summary={"error": str(e)}
            )
    
    async def schedule_cleanup_task(self) -> ExecutionResult:
        """
        Schedule and execute cleanup of expired files.
        
        Returns:
            Execution result with cleanup statistics
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Run cleanup on all containers
            result = await self._blob_manager.cleanup_expired_files()
            
            logger.info(f"Scheduled cleanup completed: {result.message}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute scheduled cleanup: {str(e)}")
            return ExecutionResult(
                function_name="schedule_cleanup_task",
                execution_id=generate_execution_id(),
                status=FunctionStatus.FAILED,
                start_time=utc_now(),
                end_time=utc_now(),
                error_message=str(e),
                output_summary={"error": str(e)}
            )
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about blob storage usage.
        
        Returns:
            Dictionary containing storage statistics
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            stats = {}
            
            # Get statistics for each container
            containers = [
                self._blob_manager.temp_container,
                self._blob_manager.processing_container,
                self._blob_manager.archive_container
            ]
            
            for container_name in containers:
                files = await self._blob_manager.list_files(
                    container_name=container_name,
                    include_metadata=True
                )
                
                total_size = sum(file_info.get("size", 0) for file_info in files)
                
                stats[container_name] = {
                    "file_count": len(files),
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2)
                }
            
            logger.info("Retrieved blob storage statistics")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {str(e)}")
            raise
    
    async def close(self) -> None:
        """Close the blob storage integration and clean up resources."""
        if self._blob_manager:
            await self._blob_manager.close()
        self._initialized = False
        logger.info("Blob storage integration closed")


# Global instance for easy access
blob_storage_integration = BlobStorageIntegration()