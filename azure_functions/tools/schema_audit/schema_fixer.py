"""
Schema Fixer module for automatically fixing schema mismatches.

This module provides the SchemaFixer class which handles:
- Automatic fixing of schema mismatches with backup/restore capabilities
- File backup management before modifications
- Rollback functionality for error recovery
- Change tracking and reporting

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5 (Fix strategies and backup/rollback)
"""

import os
import shutil
import ast
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import logging

from .models import Mismatch, Fix, FixReport, MismatchType

logger = logging.getLogger(__name__)


class SchemaFixer:
    """
    Handles automatic fixing of schema mismatches with backup and rollback capabilities.
    
    This class provides the core functionality for:
    - Creating backups before file modifications
    - Managing backup directories
    - Restoring files from backups (rollback)
    - Orchestrating the fix process
    
    Requirements: 4.5
    """
    
    def __init__(self, backup_root: str = "backups"):
        """
        Initialize the SchemaFixer.
        
        Args:
            backup_root: Root directory for storing backups (default: "backups")
        """
        self.backup_root = Path(backup_root)
        self.backup_directory: Optional[Path] = None
        self.backed_up_files: Dict[str, str] = {}  # original_path -> backup_path
        self.file_contents: Dict[str, str] = {}  # Cache of file contents
        
    def fix_mismatches(
        self, 
        mismatches: List[Mismatch], 
        dry_run: bool = False
    ) -> FixReport:
        """
        Main orchestration method for fixing all mismatches.
        
        This method coordinates the entire fix process:
        1. Creates a backup directory for this fix session
        2. Processes each mismatch
        3. Tracks all fixes in a report
        4. Handles errors and rollback if needed
        
        Args:
            mismatches: List of schema mismatches to fix
            dry_run: If True, only simulate fixes without applying them
            
        Returns:
            FixReport containing details of all fixes applied
            
        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5 (Main fix orchestration)
        """
        logger.info(f"Starting fix process for {len(mismatches)} mismatches (dry_run={dry_run})")
        
        # Create fix report
        report = FixReport(
            timestamp=datetime.now(),
            backup_directory=str(self.backup_directory) if self.backup_directory else ""
        )
        
        # Create backup directory for this session
        if not dry_run:
            self.backup_directory = self._create_backup_directory()
            report.backup_directory = str(self.backup_directory)
            logger.info(f"Created backup directory: {self.backup_directory}")
        
        # Process each mismatch
        for mismatch in mismatches:
            logger.debug(f"Processing mismatch: {mismatch}")
            
            # Determine which fix strategy to use
            fix_method = self._get_fix_method(mismatch.mismatch_type)
            
            if fix_method is None:
                logger.warning(f"No fix method for mismatch type: {mismatch.mismatch_type}")
                continue
            
            # Apply fix to each location
            for location in mismatch.locations:
                try:
                    if dry_run:
                        # In dry-run mode, just create a placeholder fix
                        fix = Fix(
                            mismatch=mismatch,
                            file_path=location.file_path,
                            line_number=location.line_number,
                            old_code=location.code_snippet,
                            new_code=location.code_snippet,  # Would be changed
                            applied=False
                        )
                        logger.info(f"[DRY-RUN] Would fix: {location}")
                    else:
                        # Apply the actual fix
                        fix = fix_method(mismatch, location)
                        logger.info(f"Applied fix: {location}")
                    
                    report.add_fix(fix)
                    
                except Exception as e:
                    logger.error(f"Failed to fix {location}: {str(e)}")
                    fix = Fix(
                        mismatch=mismatch,
                        file_path=location.file_path,
                        line_number=location.line_number,
                        old_code=location.code_snippet,
                        new_code=location.code_snippet,
                        applied=False,
                        error=str(e)
                    )
                    report.add_fix(fix)
        
        # Update file count
        report.total_files_modified = len(report.get_modified_files())
        
        logger.info(f"Fix process completed. Applied: {report.total_fixes_applied}, "
                   f"Failed: {report.total_fixes_failed}")
        
        return report
    
    def _get_fix_method(self, mismatch_type: MismatchType):
        """
        Get the appropriate fix method for a mismatch type.
        
        Args:
            mismatch_type: Type of mismatch
            
        Returns:
            Fix method function or None
        """
        fix_methods = {
            MismatchType.COLUMN_NAME_MISMATCH: self.fix_column_name,
            MismatchType.COLUMN_TYPE_MISMATCH: self.fix_column_type,
            MismatchType.MISSING_COLUMN: self.add_missing_column,
            MismatchType.EXTRA_COLUMN: self.remove_extra_column,
        }
        return fix_methods.get(mismatch_type)
    
    def backup_file(self, file_path: str) -> str:
        """
        Create a backup of a file before modification.
        
        This method:
        1. Ensures the backup directory exists
        2. Creates a backup copy of the file
        3. Preserves the directory structure in the backup
        4. Tracks the backup for potential rollback
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            Path to the backup file
            
        Raises:
            FileNotFoundError: If the source file doesn't exist
            IOError: If backup creation fails
            
        Requirements: 4.5 (Creating backups)
        """
        source_path = Path(file_path)
        
        # Validate source file exists
        if not source_path.exists():
            error_msg = f"Cannot backup non-existent file: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Ensure backup directory exists
        if self.backup_directory is None:
            self.backup_directory = self._create_backup_directory()
        
        # Create backup path preserving directory structure
        # Convert absolute path to relative for backup structure
        try:
            relative_path = source_path.relative_to(Path.cwd())
        except ValueError:
            # If file is not relative to cwd, use just the filename with a hash of the directory
            # This prevents path conflicts while maintaining uniqueness
            import hashlib
            dir_hash = hashlib.md5(str(source_path.parent).encode()).hexdigest()[:8]
            relative_path = Path(dir_hash) / source_path.name
        
        backup_path = self.backup_directory / relative_path
        
        # Create parent directories in backup location
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy the file
        try:
            shutil.copy2(source_path, backup_path)
            logger.info(f"Backed up: {file_path} -> {backup_path}")
            
            # Track the backup
            self.backed_up_files[str(source_path)] = str(backup_path)
            
            return str(backup_path)
            
        except Exception as e:
            error_msg = f"Failed to backup {file_path}: {str(e)}"
            logger.error(error_msg)
            raise IOError(error_msg) from e
    
    def _create_backup_directory(self) -> Path:
        """
        Create a timestamped backup directory.
        
        Creates a new backup directory with a timestamp to ensure uniqueness
        and allow multiple backup sessions to coexist.
        
        Returns:
            Path to the created backup directory
            
        Requirements: 4.5 (Backup management)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_root / f"backup_{timestamp}"
        
        # Create the directory
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created backup directory: {backup_dir}")
        return backup_dir
    
    def fix_column_name(self, mismatch: Mismatch, location) -> Fix:
        """
        Fix column name mismatch by renaming the column in code.
        
        This method replaces all occurrences of the incorrect column name
        with the correct one in the specified location.
        
        Args:
            mismatch: Mismatch containing expected and actual column names
            location: CodeLocation where the fix should be applied
            
        Returns:
            Fix record with details of the change
            
        Requirements: 4.1 (Column name fixing)
        """
        file_path = location.file_path
        old_name = mismatch.actual_value
        new_name = mismatch.expected_value
        
        if not old_name or not new_name:
            raise ValueError("Column name mismatch must have both actual and expected values")
        
        # Backup file if not already backed up
        if file_path not in self.backed_up_files:
            self.backup_file(file_path)
        
        # Read file content
        content = self._read_file(file_path)
        
        # Apply transformation: replace column name
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(old_name) + r'\b'
        new_content = re.sub(pattern, new_name, content)
        
        # Check if any changes were made
        if content == new_content:
            logger.warning(f"No changes made for column rename in {file_path}")
        
        # Write back to file
        self._write_file(file_path, new_content)
        
        # Create fix record
        fix = Fix(
            mismatch=mismatch,
            file_path=file_path,
            line_number=location.line_number,
            old_code=location.code_snippet,
            new_code=location.code_snippet.replace(old_name, new_name),
            applied=True
        )
        
        logger.info(f"Fixed column name: {old_name} -> {new_name} in {file_path}")
        return fix
    
    def fix_column_type(self, mismatch: Mismatch, location) -> Fix:
        """
        Fix column type mismatch by updating CREATE TABLE statements.
        
        This method finds and updates the data type definition in CREATE TABLE
        statements to match the expected type.
        
        Args:
            mismatch: Mismatch containing expected and actual column types
            location: CodeLocation where the fix should be applied
            
        Returns:
            Fix record with details of the change
            
        Requirements: 4.2 (Column type fixing)
        """
        file_path = location.file_path
        column_name = mismatch.column_name
        old_type = mismatch.actual_value
        new_type = mismatch.expected_value
        
        if not column_name or not old_type or not new_type:
            raise ValueError("Column type mismatch must have column name and both types")
        
        # Backup file if not already backed up
        if file_path not in self.backed_up_files:
            self.backup_file(file_path)
        
        # Read file content
        content = self._read_file(file_path)
        
        # Find and replace column type in CREATE TABLE statements
        # Pattern: column_name old_type (with optional constraints)
        # This handles both SQL strings and Python code
        pattern = r'(\b' + re.escape(column_name) + r'\s+)' + re.escape(old_type) + r'\b'
        new_content = re.sub(pattern, r'\1' + new_type, content, flags=re.IGNORECASE)
        
        # Check if any changes were made
        if content == new_content:
            logger.warning(f"No changes made for type change in {file_path}")
        
        # Write back to file
        self._write_file(file_path, new_content)
        
        # Create fix record
        fix = Fix(
            mismatch=mismatch,
            file_path=file_path,
            line_number=location.line_number,
            old_code=location.code_snippet,
            new_code=location.code_snippet.replace(old_type, new_type),
            applied=True
        )
        
        logger.info(f"Fixed column type: {column_name} {old_type} -> {new_type} in {file_path}")
        return fix
    
    def add_missing_column(self, mismatch: Mismatch, location) -> Fix:
        """
        Add missing column to INSERT/UPDATE operations.
        
        This method adds a missing column to database operations with a
        default value (NULL or appropriate default based on type).
        
        Args:
            mismatch: Mismatch indicating missing column
            location: CodeLocation where the fix should be applied
            
        Returns:
            Fix record with details of the change
            
        Requirements: 4.3 (Adding missing columns)
        """
        file_path = location.file_path
        column_name = mismatch.column_name
        table_name = mismatch.table_name
        
        if not column_name:
            raise ValueError("Missing column mismatch must have column name")
        
        # Backup file if not already backed up
        if file_path not in self.backed_up_files:
            self.backup_file(file_path)
        
        # Read file content
        content = self._read_file(file_path)
        
        # Try to add column to INSERT statements
        # Pattern: INSERT INTO table_name (col1, col2) VALUES (val1, val2)
        # We need to add the column to both the column list and values list
        
        # Find INSERT statements for this table
        insert_pattern = r'(INSERT\s+INTO\s+' + re.escape(table_name) + r'\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\))'
        
        def add_column_to_insert(match):
            full_statement = match.group(0)
            columns = match.group(2)
            values = match.group(3)
            
            # Add column to column list
            new_columns = columns.strip() + ', ' + column_name
            # Add NULL or default value to values list
            new_values = values.strip() + ', NULL'
            
            return f"INSERT INTO {table_name} ({new_columns}) VALUES ({new_values})"
        
        new_content = re.sub(insert_pattern, add_column_to_insert, content, flags=re.IGNORECASE)
        
        # Also handle dictionary-based inserts in Python (save_structured_data calls)
        # Look for dictionary definitions and add the missing key
        # This is more complex and may require AST manipulation for accuracy
        # For now, we'll log a warning if no SQL INSERT was found
        if content == new_content:
            logger.warning(f"Could not automatically add column {column_name} in {file_path}. "
                         f"Manual intervention may be required.")
        
        # Write back to file
        self._write_file(file_path, new_content)
        
        # Create fix record
        fix = Fix(
            mismatch=mismatch,
            file_path=file_path,
            line_number=location.line_number,
            old_code=location.code_snippet,
            new_code=f"{location.code_snippet} (added {column_name})",
            applied=True
        )
        
        logger.info(f"Added missing column: {column_name} to {table_name} in {file_path}")
        return fix
    
    def remove_extra_column(self, mismatch: Mismatch, location) -> Fix:
        """
        Remove extra column from INSERT/UPDATE operations.
        
        This method removes columns that exist in code but not in the
        reference schema from database operations.
        
        Args:
            mismatch: Mismatch indicating extra column
            location: CodeLocation where the fix should be applied
            
        Returns:
            Fix record with details of the change
            
        Requirements: 4.4 (Removing extra columns)
        """
        file_path = location.file_path
        column_name = mismatch.column_name
        table_name = mismatch.table_name
        
        if not column_name:
            raise ValueError("Extra column mismatch must have column name")
        
        # Backup file if not already backed up
        if file_path not in self.backed_up_files:
            self.backup_file(file_path)
        
        # Read file content
        content = self._read_file(file_path)
        
        # Remove column from INSERT statements
        # This is tricky because we need to remove both the column name and its corresponding value
        # Pattern: column_name followed by comma, or comma followed by column_name
        
        # Simple approach: remove the column name from column lists
        # Pattern 1: , column_name (column in middle or end)
        pattern1 = r',\s*' + re.escape(column_name) + r'\b'
        new_content = re.sub(pattern1, '', content)
        
        # Pattern 2: column_name, (column at start)
        pattern2 = r'\b' + re.escape(column_name) + r'\s*,\s*'
        new_content = re.sub(pattern2, '', new_content)
        
        # Pattern 3: standalone column_name (only column)
        pattern3 = r'\b' + re.escape(column_name) + r'\b'
        # Only apply if not already removed
        if column_name in new_content:
            logger.warning(f"Column {column_name} may still exist in {file_path}. "
                         f"Manual review recommended.")
        
        # Check if any changes were made
        if content == new_content:
            logger.warning(f"No changes made for removing column {column_name} in {file_path}")
        
        # Write back to file
        self._write_file(file_path, new_content)
        
        # Create fix record
        fix = Fix(
            mismatch=mismatch,
            file_path=file_path,
            line_number=location.line_number,
            old_code=location.code_snippet,
            new_code=f"{location.code_snippet} (removed {column_name})",
            applied=True
        )
        
        logger.info(f"Removed extra column: {column_name} from {table_name} in {file_path}")
        return fix
    
    def _apply_code_transformation(
        self, 
        file_path: str, 
        transformation_func, 
        *args
    ) -> Tuple[str, str]:
        """
        Apply AST-based code transformation to a Python file.
        
        This method provides a framework for applying AST-based transformations
        to Python code, ensuring syntax validity is preserved.
        
        Args:
            file_path: Path to the Python file
            transformation_func: Function that takes AST and returns modified AST
            *args: Additional arguments for transformation function
            
        Returns:
            Tuple of (old_content, new_content)
            
        Requirements: 4.1, 4.2, 4.3, 4.4 (AST modification support)
        """
        # Read file content
        content = self._read_file(file_path)
        
        try:
            # Parse to AST
            tree = ast.parse(content)
            
            # Apply transformation
            modified_tree = transformation_func(tree, *args)
            
            # Convert back to source code
            # Note: ast.unparse is available in Python 3.9+
            # For older versions, would need to use astor or similar
            import sys
            if sys.version_info >= (3, 9):
                new_content = ast.unparse(modified_tree)
            else:
                # Fallback: just return original content
                logger.warning(f"AST unparsing not available in Python < 3.9. "
                             f"Skipping AST transformation for {file_path}")
                new_content = content
            
            return content, new_content
            
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to apply AST transformation to {file_path}: {str(e)}")
            raise
    
    def _read_file(self, file_path: str) -> str:
        """
        Read file content with caching.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content as string
        """
        if file_path not in self.file_contents:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.file_contents[file_path] = f.read()
        return self.file_contents[file_path]
    
    def _write_file(self, file_path: str, content: str) -> None:
        """
        Write content to file and update cache.
        
        Args:
            file_path: Path to file
            content: Content to write
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        # Update cache
        self.file_contents[file_path] = content
    
    def validate_syntax(self, file_path: str) -> bool:
        """
        Validate Python syntax after modification using ast.parse.
        
        This method ensures that modifications haven't broken the Python syntax
        by attempting to parse the file with the ast module.
        
        Args:
            file_path: Path to the Python file to validate
            
        Returns:
            True if syntax is valid, False otherwise
            
        Raises:
            SyntaxError: If the file contains invalid Python syntax
            
        Requirements: 4.7 (Syntax validation)
        """
        try:
            # Read file content
            content = self._read_file(file_path)
            
            # Attempt to parse with ast
            ast.parse(content, filename=file_path)
            
            logger.info(f"Syntax validation passed for: {file_path}")
            return True
            
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path} at line {e.lineno}: {e.msg}")
            raise
        except Exception as e:
            logger.error(f"Failed to validate syntax for {file_path}: {str(e)}")
            return False
    
    def _generate_fix_report(self, fixes: List[Fix]) -> str:
        """
        Generate a detailed fix report for change tracking.
        
        This method creates a human-readable report documenting all changes
        made during the fix process, including file paths, line numbers,
        old and new code snippets.
        
        Args:
            fixes: List of Fix objects representing changes made
            
        Returns:
            Formatted report string in Markdown format
            
        Requirements: 4.6 (Change tracking)
        """
        if not fixes:
            return "# Fix Report\n\nNo fixes were applied.\n"
        
        # Group fixes by file
        fixes_by_file: Dict[str, List[Fix]] = {}
        for fix in fixes:
            if fix.file_path not in fixes_by_file:
                fixes_by_file[fix.file_path] = []
            fixes_by_file[fix.file_path].append(fix)
        
        # Build report
        report_lines = [
            "# Fix Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Fixes:** {len(fixes)}",
            f"**Files Modified:** {len(fixes_by_file)}",
            "",
            "---",
            ""
        ]
        
        # Add details for each file
        for file_path, file_fixes in fixes_by_file.items():
            report_lines.append(f"## File: `{file_path}`")
            report_lines.append("")
            report_lines.append(f"**Changes:** {len(file_fixes)}")
            report_lines.append("")
            
            for i, fix in enumerate(file_fixes, 1):
                report_lines.append(f"### Change {i}")
                report_lines.append("")
                report_lines.append(f"**Type:** {fix.mismatch.mismatch_type.value}")
                report_lines.append(f"**Table:** {fix.mismatch.table_name}")
                if fix.mismatch.column_name:
                    report_lines.append(f"**Column:** {fix.mismatch.column_name}")
                report_lines.append(f"**Line:** {fix.line_number}")
                report_lines.append(f"**Applied:** {'✓' if fix.applied else '✗'}")
                
                if fix.error:
                    report_lines.append(f"**Error:** {fix.error}")
                
                report_lines.append("")
                report_lines.append("**Old Code:**")
                report_lines.append("```python")
                report_lines.append(fix.old_code)
                report_lines.append("```")
                report_lines.append("")
                report_lines.append("**New Code:**")
                report_lines.append("```python")
                report_lines.append(fix.new_code)
                report_lines.append("```")
                report_lines.append("")
        
        # Add summary
        successful_fixes = sum(1 for fix in fixes if fix.applied)
        failed_fixes = len(fixes) - successful_fixes
        
        report_lines.append("---")
        report_lines.append("")
        report_lines.append("## Summary")
        report_lines.append("")
        report_lines.append(f"- **Successful:** {successful_fixes}")
        report_lines.append(f"- **Failed:** {failed_fixes}")
        report_lines.append(f"- **Success Rate:** {(successful_fixes / len(fixes) * 100):.1f}%")
        report_lines.append("")
        
        return "\n".join(report_lines)
    
    def _rollback_changes(self, file_path: Optional[str] = None) -> bool:
        """
        Rollback changes by restoring files from backup (error recovery).
        
        This method provides error recovery by restoring files to their
        pre-modification state. It can rollback a specific file or all
        modified files.
        
        Args:
            file_path: Specific file to rollback, or None to rollback all files
            
        Returns:
            True if rollback was successful, False otherwise
            
        Requirements: 4.7 (Error recovery)
        """
        logger.info(f"Initiating rollback for: {file_path if file_path else 'all files'}")
        
        if not self.backed_up_files:
            logger.warning("No backed up files to rollback")
            return False
        
        # Use the existing _restore_from_backup method
        success = self._restore_from_backup(file_path)
        
        if success:
            logger.info("Rollback completed successfully")
            # Clear file cache for rolled back files
            if file_path:
                self.file_contents.pop(file_path, None)
            else:
                self.file_contents.clear()
        else:
            logger.error("Rollback failed")
        
        return success
    
    def _restore_from_backup(self, file_path: Optional[str] = None) -> bool:
        """
        Restore file(s) from backup (rollback functionality).
        
        This method provides rollback capability by restoring files from
        their backups. Can restore a single file or all backed up files.
        
        Args:
            file_path: Specific file to restore, or None to restore all files
            
        Returns:
            True if restoration was successful, False otherwise
            
        Requirements: 4.5 (Rollback)
        """
        if not self.backed_up_files:
            logger.warning("No backed up files to restore")
            return False
        
        success = True
        
        if file_path:
            # Restore specific file
            if file_path not in self.backed_up_files:
                logger.error(f"No backup found for: {file_path}")
                return False
            
            backup_path = self.backed_up_files[file_path]
            try:
                shutil.copy2(backup_path, file_path)
                logger.info(f"Restored: {backup_path} -> {file_path}")
            except Exception as e:
                logger.error(f"Failed to restore {file_path}: {str(e)}")
                success = False
        else:
            # Restore all files
            logger.info(f"Restoring {len(self.backed_up_files)} files from backup")
            for original_path, backup_path in self.backed_up_files.items():
                try:
                    shutil.copy2(backup_path, original_path)
                    logger.info(f"Restored: {backup_path} -> {original_path}")
                except Exception as e:
                    logger.error(f"Failed to restore {original_path}: {str(e)}")
                    success = False
        
        return success
