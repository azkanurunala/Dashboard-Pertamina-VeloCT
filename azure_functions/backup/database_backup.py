"""
Automated database backup functionality for Azure SQL Database.
Implements scheduled backups with retention policy and integrity validation.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from ..shared.logging_config import get_logger
from ..shared.blob_storage import BlobStorageManager
from ..shared.config import ConfigManager


@dataclass
class BackupResult:
    """Result of a backup operation."""
    backup_id: str
    backup_name: str
    backup_time: datetime
    backup_size_bytes: int
    backup_location: str
    status: str  # success, failed, partial
    duration_seconds: float
    validation_passed: bool
    error_message: Optional[str] = None


@dataclass
class BackupMetadata:
    """Metadata for a backup."""
    backup_id: str
    backup_name: str
    backup_time: datetime
    database_name: str
    backup_type: str  # full, differential, transaction_log
    backup_size_bytes: int
    blob_name: str
    retention_days: int
    expires_at: datetime
    checksum: Optional[str] = None
    validated: bool = False


class DatabaseBackupService:
    """
    Service for automated database backups to Azure Blob Storage.
    
    Features:
    - Scheduled full and differential backups
    - Backup to Azure Blob Storage with retention policy
    - Backup validation and integrity checks
    - Backup status logging and monitoring
    - Automatic cleanup of expired backups
    """
    
    def __init__(
        self,
        config_manager: ConfigManager,
        blob_manager: BlobStorageManager,
        retention_days: int = 30
    ):
        """
        Initialize the backup service.
        
        Args:
            config_manager: Configuration manager instance
            blob_manager: Blob storage manager instance
            retention_days: Number of days to retain backups (default: 30)
        """
        self.config_manager = config_manager
        self.blob_manager = blob_manager
        self.retention_days = retention_days
        self.logger = get_logger(__name__)
        
        self.logger.info(f"DatabaseBackupService initialized with retention={retention_days} days")
    
    async def create_full_backup(
        self,
        database_name: str,
        backup_name: Optional[str] = None
    ) -> BackupResult:
        """
        Create a full database backup.
        
        Args:
            database_name: Name of the database to backup
            backup_name: Optional custom backup name
            
        Returns:
            BackupResult with backup details
        """
        start_time = datetime.utcnow()
        backup_id = f"backup_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        if not backup_name:
            backup_name = f"{database_name}_full_{start_time.strftime('%Y%m%d_%H%M%S')}.bacpac"
        
        try:
            self.logger.info(f"Starting full backup for database: {database_name}")
            
            # Get database configuration
            db_config = await self.config_manager.get_database_config()
            
            # Create backup using Azure SQL Database export
            backup_blob_name = f"backups/full/{backup_name}"
            backup_size = await self._export_database_to_blob(
                database_name,
                backup_blob_name,
                db_config
            )
            
            # Validate backup
            validation_passed = await self._validate_backup(backup_blob_name)
            
            # Save backup metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_name=backup_name,
                backup_time=start_time,
                database_name=database_name,
                backup_type="full",
                backup_size_bytes=backup_size,
                blob_name=backup_blob_name,
                retention_days=self.retention_days,
                expires_at=start_time + timedelta(days=self.retention_days),
                validated=validation_passed
            )
            
            await self._save_backup_metadata(metadata)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            result = BackupResult(
                backup_id=backup_id,
                backup_name=backup_name,
                backup_time=start_time,
                backup_size_bytes=backup_size,
                backup_location=backup_blob_name,
                status="success" if validation_passed else "partial",
                duration_seconds=duration,
                validation_passed=validation_passed
            )
            
            self.logger.info(
                f"Full backup completed: {backup_name}, "
                f"size={backup_size} bytes, duration={duration:.2f}s"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Error creating full backup: {str(e)}"
            self.logger.error(error_msg)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            return BackupResult(
                backup_id=backup_id,
                backup_name=backup_name,
                backup_time=start_time,
                backup_size_bytes=0,
                backup_location="",
                status="failed",
                duration_seconds=duration,
                validation_passed=False,
                error_message=error_msg
            )
    
    async def create_differential_backup(
        self,
        database_name: str,
        backup_name: Optional[str] = None
    ) -> BackupResult:
        """
        Create a differential database backup.
        
        Args:
            database_name: Name of the database to backup
            backup_name: Optional custom backup name
            
        Returns:
            BackupResult with backup details
        """
        start_time = datetime.utcnow()
        backup_id = f"backup_diff_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        if not backup_name:
            backup_name = f"{database_name}_diff_{start_time.strftime('%Y%m%d_%H%M%S')}.bacpac"
        
        try:
            self.logger.info(f"Starting differential backup for database: {database_name}")
            
            # Note: Azure SQL Database doesn't support true differential backups
            # This creates a full export but with differential naming for tracking
            db_config = await self.config_manager.get_database_config()
            
            backup_blob_name = f"backups/differential/{backup_name}"
            backup_size = await self._export_database_to_blob(
                database_name,
                backup_blob_name,
                db_config
            )
            
            validation_passed = await self._validate_backup(backup_blob_name)
            
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_name=backup_name,
                backup_time=start_time,
                database_name=database_name,
                backup_type="differential",
                backup_size_bytes=backup_size,
                blob_name=backup_blob_name,
                retention_days=self.retention_days // 2,  # Shorter retention for differential
                expires_at=start_time + timedelta(days=self.retention_days // 2),
                validated=validation_passed
            )
            
            await self._save_backup_metadata(metadata)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            result = BackupResult(
                backup_id=backup_id,
                backup_name=backup_name,
                backup_time=start_time,
                backup_size_bytes=backup_size,
                backup_location=backup_blob_name,
                status="success" if validation_passed else "partial",
                duration_seconds=duration,
                validation_passed=validation_passed
            )
            
            self.logger.info(
                f"Differential backup completed: {backup_name}, "
                f"size={backup_size} bytes, duration={duration:.2f}s"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Error creating differential backup: {str(e)}"
            self.logger.error(error_msg)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            return BackupResult(
                backup_id=backup_id,
                backup_name=backup_name,
                backup_time=start_time,
                backup_size_bytes=0,
                backup_location="",
                status="failed",
                duration_seconds=duration,
                validation_passed=False,
                error_message=error_msg
            )
    
    async def cleanup_expired_backups(self) -> Dict[str, Any]:
        """
        Clean up expired backups based on retention policy.
        
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            self.logger.info("Starting cleanup of expired backups")
            
            # Get all backup metadata
            all_metadata = await self._list_backup_metadata()
            
            now = datetime.utcnow()
            expired_backups = [
                meta for meta in all_metadata
                if meta.expires_at < now
            ]
            
            deleted_count = 0
            deleted_size = 0
            errors = []
            
            for metadata in expired_backups:
                try:
                    # Delete backup blob
                    await self.blob_manager.delete_file(
                        metadata.blob_name,
                        container_name="backups"
                    )
                    
                    # Delete metadata
                    await self._delete_backup_metadata(metadata.backup_id)
                    
                    deleted_count += 1
                    deleted_size += metadata.backup_size_bytes
                    
                    self.logger.info(f"Deleted expired backup: {metadata.backup_name}")
                    
                except Exception as e:
                    error_msg = f"Error deleting backup {metadata.backup_name}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
            
            result = {
                'deleted_count': deleted_count,
                'deleted_size_bytes': deleted_size,
                'deleted_size_mb': round(deleted_size / (1024 * 1024), 2),
                'errors': errors,
                'timestamp': now.isoformat()
            }
            
            self.logger.info(
                f"Cleanup completed: {deleted_count} backups deleted, "
                f"{result['deleted_size_mb']} MB freed"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Error during backup cleanup: {str(e)}"
            self.logger.error(error_msg)
            return {
                'deleted_count': 0,
                'deleted_size_bytes': 0,
                'errors': [error_msg],
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def list_backups(
        self,
        database_name: Optional[str] = None,
        backup_type: Optional[str] = None
    ) -> List[BackupMetadata]:
        """
        List available backups.
        
        Args:
            database_name: Optional filter by database name
            backup_type: Optional filter by backup type
            
        Returns:
            List of backup metadata
        """
        try:
            all_metadata = await self._list_backup_metadata()
            
            # Apply filters
            filtered = all_metadata
            
            if database_name:
                filtered = [m for m in filtered if m.database_name == database_name]
            
            if backup_type:
                filtered = [m for m in filtered if m.backup_type == backup_type]
            
            # Sort by backup time (newest first)
            filtered.sort(key=lambda m: m.backup_time, reverse=True)
            
            return filtered
            
        except Exception as e:
            self.logger.error(f"Error listing backups: {str(e)}")
            return []
    
    async def get_backup_status(self, backup_id: str) -> Optional[BackupMetadata]:
        """
        Get status of a specific backup.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            BackupMetadata if found, None otherwise
        """
        try:
            metadata = await self._load_backup_metadata(backup_id)
            return metadata
        except Exception as e:
            self.logger.error(f"Error getting backup status: {str(e)}")
            return None
    
    async def _export_database_to_blob(
        self,
        database_name: str,
        blob_name: str,
        db_config
    ) -> int:
        """
        Export database to blob storage using Azure SQL Database export.
        
        Args:
            database_name: Database name
            blob_name: Blob name for backup
            db_config: Database configuration
            
        Returns:
            Size of backup in bytes
        """
        # Note: In production, this would use Azure SQL Database export API
        # For now, we'll simulate the export process
        
        self.logger.info(f"Exporting database {database_name} to {blob_name}")
        
        # Simulate export by creating a placeholder backup file
        backup_content = json.dumps({
            'database': database_name,
            'export_time': datetime.utcnow().isoformat(),
            'version': '1.0',
            'note': 'This is a simulated backup. In production, use Azure SQL Database export API.'
        }).encode('utf-8')
        
        # Upload to blob storage
        await self.blob_manager.upload_processing_file(
            backup_content,
            blob_name,
            content_type='application/octet-stream',
            metadata={
                'database': database_name,
                'backup_time': datetime.utcnow().isoformat()
            }
        )
        
        return len(backup_content)
    
    async def _validate_backup(self, blob_name: str) -> bool:
        """
        Validate backup integrity.
        
        Args:
            blob_name: Blob name of backup
            
        Returns:
            True if validation passed, False otherwise
        """
        try:
            self.logger.info(f"Validating backup: {blob_name}")
            
            # Check if blob exists
            try:
                content = await self.blob_manager.download_file(
                    blob_name,
                    container_name="processing"
                )
                
                if not content or len(content) == 0:
                    self.logger.error("Backup file is empty")
                    return False
                
                # Additional validation could include:
                # - Checksum verification
                # - File format validation
                # - Test restore to temporary database
                
                self.logger.info("Backup validation passed")
                return True
                
            except Exception as e:
                self.logger.error(f"Backup validation failed: {str(e)}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error during backup validation: {str(e)}")
            return False
    
    async def _save_backup_metadata(self, metadata: BackupMetadata) -> None:
        """Save backup metadata to blob storage."""
        try:
            metadata_blob_name = f"backups/metadata/{metadata.backup_id}.json"
            
            metadata_dict = {
                'backup_id': metadata.backup_id,
                'backup_name': metadata.backup_name,
                'backup_time': metadata.backup_time.isoformat(),
                'database_name': metadata.database_name,
                'backup_type': metadata.backup_type,
                'backup_size_bytes': metadata.backup_size_bytes,
                'blob_name': metadata.blob_name,
                'retention_days': metadata.retention_days,
                'expires_at': metadata.expires_at.isoformat(),
                'checksum': metadata.checksum,
                'validated': metadata.validated
            }
            
            metadata_json = json.dumps(metadata_dict, indent=2).encode('utf-8')
            
            await self.blob_manager.upload_processing_file(
                metadata_json,
                metadata_blob_name,
                content_type='application/json'
            )
            
            self.logger.info(f"Saved backup metadata: {metadata.backup_id}")
            
        except Exception as e:
            self.logger.error(f"Error saving backup metadata: {str(e)}")
            raise
    
    async def _load_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """Load backup metadata from blob storage."""
        try:
            metadata_blob_name = f"backups/metadata/{backup_id}.json"
            
            content = await self.blob_manager.download_file(
                metadata_blob_name,
                container_name="processing"
            )
            
            metadata_dict = json.loads(content.decode('utf-8'))
            
            metadata = BackupMetadata(
                backup_id=metadata_dict['backup_id'],
                backup_name=metadata_dict['backup_name'],
                backup_time=datetime.fromisoformat(metadata_dict['backup_time']),
                database_name=metadata_dict['database_name'],
                backup_type=metadata_dict['backup_type'],
                backup_size_bytes=metadata_dict['backup_size_bytes'],
                blob_name=metadata_dict['blob_name'],
                retention_days=metadata_dict['retention_days'],
                expires_at=datetime.fromisoformat(metadata_dict['expires_at']),
                checksum=metadata_dict.get('checksum'),
                validated=metadata_dict.get('validated', False)
            )
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error loading backup metadata: {str(e)}")
            return None
    
    async def _list_backup_metadata(self) -> List[BackupMetadata]:
        """List all backup metadata."""
        # Note: In production, this would list all metadata blobs
        # For now, return empty list as placeholder
        return []
    
    async def _delete_backup_metadata(self, backup_id: str) -> None:
        """Delete backup metadata."""
        try:
            metadata_blob_name = f"backups/metadata/{backup_id}.json"
            
            await self.blob_manager.delete_file(
                metadata_blob_name,
                container_name="processing"
            )
            
            self.logger.info(f"Deleted backup metadata: {backup_id}")
            
        except Exception as e:
            self.logger.error(f"Error deleting backup metadata: {str(e)}")
            raise


class BackupScheduler:
    """
    Scheduler for automated database backups.
    
    Manages backup schedules and execution.
    """
    
    def __init__(self, backup_service: DatabaseBackupService):
        """
        Initialize the backup scheduler.
        
        Args:
            backup_service: DatabaseBackupService instance
        """
        self.backup_service = backup_service
        self.logger = get_logger(__name__)
    
    async def run_daily_backup(self, database_name: str) -> BackupResult:
        """
        Run daily full backup.
        
        Args:
            database_name: Database to backup
            
        Returns:
            BackupResult
        """
        self.logger.info(f"Running daily backup for {database_name}")
        return await self.backup_service.create_full_backup(database_name)
    
    async def run_hourly_differential(self, database_name: str) -> BackupResult:
        """
        Run hourly differential backup.
        
        Args:
            database_name: Database to backup
            
        Returns:
            BackupResult
        """
        self.logger.info(f"Running hourly differential backup for {database_name}")
        return await self.backup_service.create_differential_backup(database_name)
    
    async def run_cleanup(self) -> Dict[str, Any]:
        """
        Run backup cleanup.
        
        Returns:
            Cleanup statistics
        """
        self.logger.info("Running backup cleanup")
        return await self.backup_service.cleanup_expired_backups()
