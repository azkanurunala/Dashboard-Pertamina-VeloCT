"""
Azure Blob Storage integration for temporary file operations and large file handling.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, List, Optional, Union, BinaryIO
from pathlib import Path
import logging

from azure.storage.blob.aio import BlobServiceClient, BlobClient, ContainerClient
from azure.storage.blob import BlobProperties, ContentSettings
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from azure.identity.aio import DefaultAzureCredential

from .interfaces import ConfigurationError, IBlobStorageManager
from .utils import generate_execution_id, utc_now, sanitize_filename
from .models import ExecutionResult, FunctionStatus


logger = logging.getLogger(__name__)


class BlobStorageManager(IBlobStorageManager):
    """
    Manages Azure Blob Storage operations for temporary files and large file handling.
    """
    
    def __init__(self, connection_string: Optional[str] = None, account_url: Optional[str] = None):
        """
        Initialize the blob storage manager.
        
        Args:
            connection_string: Azure Storage connection string
            account_url: Azure Storage account URL (for managed identity auth)
        """
        self.connection_string = connection_string
        self.account_url = account_url
        self._client: Optional[BlobServiceClient] = None
        self._containers: Dict[str, ContainerClient] = {}
        
        # Default container names
        self.temp_container = "temp-files"
        self.processing_container = "processing-files"
        self.archive_container = "archive-files"
        
        # Cleanup settings
        self.temp_file_ttl_hours = 24  # Temporary files expire after 24 hours
        self.processing_file_ttl_hours = 72  # Processing files expire after 72 hours
    
    async def initialize(self) -> None:
        """Initialize the blob service client and ensure containers exist."""
        try:
            if self.connection_string:
                self._client = BlobServiceClient.from_connection_string(self.connection_string, api_version="2023-11-03")
            elif self.account_url:
                credential = DefaultAzureCredential()
                self._client = BlobServiceClient(account_url=self.account_url, credential=credential, api_version="2023-11-03")
            else:
                raise ConfigurationError("Either connection_string or account_url must be provided")
            
            # Ensure required containers exist
            await self._ensure_containers_exist()
            
            logger.info("Blob storage manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize blob storage manager: {str(e)}")
            raise ConfigurationError(f"Blob storage initialization failed: {str(e)}")
    
    async def _ensure_containers_exist(self) -> None:
        """Ensure all required containers exist."""
        containers = [self.temp_container, self.processing_container, self.archive_container]
        
        for container_name in containers:
            try:
                container_client = self._client.get_container_client(container_name)
                await container_client.create_container()
                self._containers[container_name] = container_client
                logger.info(f"Created container: {container_name}")
            except ResourceExistsError:
                # Container already exists
                self._containers[container_name] = self._client.get_container_client(container_name)
                logger.debug(f"Container already exists: {container_name}")
            except Exception as e:
                logger.error(f"Failed to create container {container_name}: {str(e)}")
                raise
    
    async def upload_temp_file(self, 
                              file_content: Union[str, bytes, BinaryIO], 
                              filename: Optional[str] = None,
                              content_type: Optional[str] = None,
                              metadata: Optional[Dict[str, str]] = None) -> str:
        """
        Upload a temporary file to blob storage.
        
        Args:
            file_content: File content (string, bytes, or file-like object)
            filename: Optional filename (auto-generated if not provided)
            content_type: MIME type of the content
            metadata: Optional metadata dictionary
            
        Returns:
            Blob name/path of the uploaded file
            
        Raises:
            Exception: If upload fails
        """
        try:
            # Generate filename if not provided
            if not filename:
                execution_id = generate_execution_id()
                timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
                filename = f"temp_{timestamp}_{execution_id[:8]}.tmp"
            else:
                filename = sanitize_filename(filename)
            
            # Add timestamp prefix for organization
            blob_name = f"{utc_now().strftime('%Y/%m/%d')}/{filename}"
            
            # Prepare metadata
            upload_metadata = {
                "upload_time": utc_now().isoformat(),
                "expires_at": (utc_now() + timedelta(hours=self.temp_file_ttl_hours)).isoformat(),
                "file_type": "temporary"
            }
            if metadata:
                upload_metadata.update(metadata)
            
            # Set content settings
            content_settings = None
            if content_type:
                content_settings = ContentSettings(content_type=content_type)
            
            # Upload the file
            container_client = self._containers[self.temp_container]
            blob_client = container_client.get_blob_client(blob_name)
            
            await blob_client.upload_blob(
                data=file_content,
                overwrite=True,
                metadata=upload_metadata,
                content_settings=content_settings
            )
            
            logger.info(f"Uploaded temporary file: {blob_name}")
            return blob_name
            
        except Exception as e:
            logger.error(f"Failed to upload temporary file: {str(e)}")
            raise
    
    async def upload_processing_file(self, 
                                   file_content: Union[str, bytes, BinaryIO],
                                   filename: str,
                                   content_type: Optional[str] = None,
                                   metadata: Optional[Dict[str, str]] = None) -> str:
        """
        Upload a file for processing operations.
        
        Args:
            file_content: File content
            filename: Filename
            content_type: MIME type of the content
            metadata: Optional metadata dictionary
            
        Returns:
            Blob name/path of the uploaded file
        """
        try:
            filename = sanitize_filename(filename)
            blob_name = f"{utc_now().strftime('%Y/%m/%d')}/{filename}"
            
            # Prepare metadata
            upload_metadata = {
                "upload_time": utc_now().isoformat(),
                "expires_at": (utc_now() + timedelta(hours=self.processing_file_ttl_hours)).isoformat(),
                "file_type": "processing"
            }
            if metadata:
                upload_metadata.update(metadata)
            
            # Set content settings
            content_settings = None
            if content_type:
                content_settings = ContentSettings(content_type=content_type)
            
            # Upload the file
            container_client = self._containers[self.processing_container]
            blob_client = container_client.get_blob_client(blob_name)
            
            await blob_client.upload_blob(
                data=file_content,
                overwrite=True,
                metadata=upload_metadata,
                content_settings=content_settings
            )
            
            logger.info(f"Uploaded processing file: {blob_name}")
            return blob_name
            
        except Exception as e:
            logger.error(f"Failed to upload processing file: {str(e)}")
            raise
    
    async def download_file(self, blob_name: str, container_name: Optional[str] = None) -> bytes:
        """
        Download a file from blob storage.
        
        Args:
            blob_name: Name/path of the blob
            container_name: Container name (defaults to temp_container)
            
        Returns:
            File content as bytes
            
        Raises:
            ResourceNotFoundError: If file not found
        """
        try:
            container_name = container_name or self.temp_container
            container_client = self._containers[container_name]
            blob_client = container_client.get_blob_client(blob_name)
            
            download_stream = await blob_client.download_blob()
            content = await download_stream.readall()
            
            logger.debug(f"Downloaded file: {blob_name}")
            return content
            
        except ResourceNotFoundError:
            logger.warning(f"File not found: {blob_name}")
            raise
        except Exception as e:
            logger.error(f"Failed to download file {blob_name}: {str(e)}")
            raise
    
    async def stream_download(self, 
                            blob_name: str, 
                            container_name: Optional[str] = None,
                            chunk_size: int = 8192) -> AsyncGenerator[bytes, None]:
        """
        Stream download a large file from blob storage.
        
        Args:
            blob_name: Name/path of the blob
            container_name: Container name (defaults to temp_container)
            chunk_size: Size of each chunk in bytes
            
        Yields:
            File content chunks as bytes
        """
        try:
            container_name = container_name or self.temp_container
            container_client = self._containers[container_name]
            blob_client = container_client.get_blob_client(blob_name)
            
            download_stream = await blob_client.download_blob()
            
            async for chunk in download_stream.chunks():
                yield chunk
                
            logger.debug(f"Streamed download completed: {blob_name}")
            
        except Exception as e:
            logger.error(f"Failed to stream download file {blob_name}: {str(e)}")
            raise
    
    async def stream_upload(self, 
                          data_stream: AsyncGenerator[bytes, None],
                          blob_name: str,
                          container_name: Optional[str] = None,
                          content_type: Optional[str] = None,
                          metadata: Optional[Dict[str, str]] = None) -> str:
        """
        Stream upload large file content to blob storage.
        
        Args:
            data_stream: Async generator yielding file chunks
            blob_name: Name/path for the blob
            container_name: Container name (defaults to processing_container)
            content_type: MIME type of the content
            metadata: Optional metadata dictionary
            
        Returns:
            Blob name/path of the uploaded file
        """
        try:
            container_name = container_name or self.processing_container
            blob_name = sanitize_filename(blob_name)
            
            # Prepare metadata
            upload_metadata = {
                "upload_time": utc_now().isoformat(),
                "file_type": "streamed_upload"
            }
            if metadata:
                upload_metadata.update(metadata)
            
            # Set content settings
            content_settings = None
            if content_type:
                content_settings = ContentSettings(content_type=content_type)
            
            container_client = self._containers[container_name]
            blob_client = container_client.get_blob_client(blob_name)
            
            # Stream upload
            await blob_client.upload_blob(
                data=data_stream,
                overwrite=True,
                metadata=upload_metadata,
                content_settings=content_settings
            )
            
            logger.info(f"Stream uploaded file: {blob_name}")
            return blob_name
            
        except Exception as e:
            logger.error(f"Failed to stream upload file: {str(e)}")
            raise
    
    async def delete_file(self, blob_name: str, container_name: Optional[str] = None) -> bool:
        """
        Delete a file from blob storage.
        
        Args:
            blob_name: Name/path of the blob to delete
            container_name: Container name (defaults to temp_container)
            
        Returns:
            True if deleted successfully, False if file didn't exist
        """
        try:
            container_name = container_name or self.temp_container
            container_client = self._containers[container_name]
            blob_client = container_client.get_blob_client(blob_name)
            
            await blob_client.delete_blob()
            logger.info(f"Deleted file: {blob_name}")
            return True
            
        except ResourceNotFoundError:
            logger.warning(f"File not found for deletion: {blob_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {blob_name}: {str(e)}")
            raise
    
    async def list_files(self, 
                        container_name: Optional[str] = None,
                        prefix: Optional[str] = None,
                        include_metadata: bool = False) -> List[Dict[str, any]]:
        """
        List files in a container.
        
        Args:
            container_name: Container name (defaults to temp_container)
            prefix: Optional prefix filter
            include_metadata: Whether to include blob metadata
            
        Returns:
            List of file information dictionaries
        """
        try:
            container_name = container_name or self.temp_container
            container_client = self._containers[container_name]
            
            files = []
            async for blob in container_client.list_blobs(name_starts_with=prefix, include=['metadata']):
                file_info = {
                    "name": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified,
                    "content_type": blob.content_settings.content_type if blob.content_settings else None
                }
                
                if include_metadata and blob.metadata:
                    file_info["metadata"] = blob.metadata
                
                files.append(file_info)
            
            logger.debug(f"Listed {len(files)} files in container {container_name}")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files in container {container_name}: {str(e)}")
            raise
    
    async def cleanup_expired_files(self, container_name: Optional[str] = None) -> ExecutionResult:
        """
        Clean up expired temporary and processing files.
        
        Args:
            container_name: Container to clean (defaults to all containers)
            
        Returns:
            Execution result with cleanup statistics
        """
        try:
            containers_to_clean = [container_name] if container_name else [
                self.temp_container, self.processing_container
            ]
            
            total_deleted = 0
            total_errors = 0
            cleanup_details = {}
            
            for container in containers_to_clean:
                deleted_count = 0
                error_count = 0
                
                try:
                    container_client = self._containers[container]
                    current_time = utc_now()
                    
                    async for blob in container_client.list_blobs(include=['metadata']):
                        try:
                            # Check if file has expired
                            if blob.metadata and 'expires_at' in blob.metadata:
                                expires_at = datetime.fromisoformat(blob.metadata['expires_at'].replace('Z', '+00:00'))
                                
                                if current_time > expires_at:
                                    blob_client = container_client.get_blob_client(blob.name)
                                    await blob_client.delete_blob()
                                    deleted_count += 1
                                    logger.debug(f"Deleted expired file: {blob.name}")
                            
                        except Exception as e:
                            error_count += 1
                            logger.error(f"Failed to delete expired file {blob.name}: {str(e)}")
                
                except Exception as e:
                    logger.error(f"Failed to cleanup container {container}: {str(e)}")
                    error_count += 1
                
                cleanup_details[container] = {
                    "deleted": deleted_count,
                    "errors": error_count
                }
                
                total_deleted += deleted_count
                total_errors += error_count
            
            result = ExecutionResult(
                function_name="cleanup_expired_files",
                execution_id=generate_execution_id(),
                status=FunctionStatus.SUCCESS if total_errors == 0 else FunctionStatus.FAILED,
                start_time=utc_now(),
                end_time=utc_now(),
                output_summary={
                    "total_deleted": total_deleted,
                    "total_errors": total_errors,
                    "details": cleanup_details
                }
            )
            
            logger.info(f"Cleanup completed: {total_deleted} files deleted, {total_errors} errors")
            return result
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired files: {str(e)}")
            return ExecutionResult(
                function_name="cleanup_expired_files",
                execution_id=generate_execution_id(),
                status=FunctionStatus.FAILED,
                start_time=utc_now(),
                end_time=utc_now(),
                error_message=str(e),
                output_summary={"error": str(e)}
            )
    
    async def get_file_info(self, blob_name: str, container_name: Optional[str] = None) -> Optional[Dict[str, any]]:
        """
        Get information about a specific file.
        
        Args:
            blob_name: Name/path of the blob
            container_name: Container name (defaults to temp_container)
            
        Returns:
            File information dictionary or None if not found
        """
        try:
            container_name = container_name or self.temp_container
            container_client = self._containers[container_name]
            blob_client = container_client.get_blob_client(blob_name)
            
            properties = await blob_client.get_blob_properties()
            
            return {
                "name": blob_name,
                "size": properties.size,
                "last_modified": properties.last_modified,
                "content_type": properties.content_settings.content_type if properties.content_settings else None,
                "metadata": properties.metadata,
                "etag": properties.etag
            }
            
        except ResourceNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get file info for {blob_name}: {str(e)}")
            raise
    
    async def copy_file(self, 
                       source_blob_name: str,
                       dest_blob_name: str,
                       source_container: Optional[str] = None,
                       dest_container: Optional[str] = None) -> bool:
        """
        Copy a file from one location to another.
        
        Args:
            source_blob_name: Source blob name/path
            dest_blob_name: Destination blob name/path
            source_container: Source container (defaults to temp_container)
            dest_container: Destination container (defaults to archive_container)
            
        Returns:
            True if copy was successful
        """
        try:
            source_container = source_container or self.temp_container
            dest_container = dest_container or self.archive_container
            
            source_client = self._containers[source_container].get_blob_client(source_blob_name)
            dest_client = self._containers[dest_container].get_blob_client(dest_blob_name)
            
            # Get source blob URL
            source_url = source_client.url
            
            # Start copy operation
            copy_props = await dest_client.start_copy_from_url(source_url)
            
            # Wait for copy to complete (for small files this should be immediate)
            while copy_props.status == 'pending':
                await asyncio.sleep(1)
                properties = await dest_client.get_blob_properties()
                copy_props = properties.copy
            
            if copy_props.status == 'success':
                logger.info(f"Successfully copied {source_blob_name} to {dest_blob_name}")
                return True
            else:
                logger.error(f"Copy failed with status: {copy_props.status}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to copy file from {source_blob_name} to {dest_blob_name}: {str(e)}")
            raise
    
    async def archive_file(self, blob_name: str, container_name: Optional[str] = None) -> bool:
        """
        Archive a file by moving it to the archive container.
        
        Args:
            blob_name: Name/path of the blob to archive
            container_name: Source container (defaults to temp_container)
            
        Returns:
            True if archival was successful
        """
        try:
            # Copy to archive container
            archive_blob_name = f"archived_{utc_now().strftime('%Y%m%d')}_{blob_name}"
            success = await self.copy_file(
                source_blob_name=blob_name,
                dest_blob_name=archive_blob_name,
                source_container=container_name,
                dest_container=self.archive_container
            )
            
            if success:
                # Delete from source container
                await self.delete_file(blob_name, container_name)
                logger.info(f"Archived file: {blob_name} -> {archive_blob_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to archive file {blob_name}: {str(e)}")
            raise
    
    async def close(self) -> None:
        """Close the blob service client and clean up resources."""
        try:
            if self._client:
                await self._client.close()
            self._containers.clear()
            logger.info("Blob storage manager closed")
        except Exception as e:
            logger.error(f"Error closing blob storage manager: {str(e)}")


# Utility functions for common blob storage operations

async def create_temp_file_from_content(content: Union[str, bytes], 
                                      filename: Optional[str] = None,
                                      blob_manager: Optional[BlobStorageManager] = None) -> str:
    """
    Create a temporary file in blob storage from content.
    
    Args:
        content: File content
        filename: Optional filename
        blob_manager: Optional blob manager instance
        
    Returns:
        Blob name of the created file
    """
    if not blob_manager:
        # This would typically be injected or retrieved from a service container
        raise ValueError("BlobStorageManager instance required")
    
    return await blob_manager.upload_temp_file(content, filename)


async def process_large_file_streaming(file_path: str, 
                                     blob_manager: BlobStorageManager,
                                     chunk_size: int = 8192) -> str:
    """
    Process a large local file by streaming it to blob storage.
    
    Args:
        file_path: Path to the local file
        blob_manager: Blob storage manager instance
        chunk_size: Size of each chunk for streaming
        
    Returns:
        Blob name of the uploaded file
    """
    async def file_chunk_generator():
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
    filename = Path(file_path).name
    return await blob_manager.stream_upload(
        data_stream=file_chunk_generator(),
        blob_name=filename,
        content_type="application/octet-stream"
    )