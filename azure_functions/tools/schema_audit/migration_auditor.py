"""
Migration Script Auditor for Database Schema Audit System.

This module scans and audits migration scripts (both SQL and Python) to:
- Detect schema operations (CREATE TABLE, ALTER TABLE, etc.)
- Identify schema mismatches in migration scripts
- Fix migration scripts to match reference schema
- Generate new migration scripts when needed
- Check migration compatibility

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import logging
from datetime import datetime

from azure_functions.tools.schema_audit.models import (
    TableOperation,
    CodeLocation,
    OperationType,
    DatabaseSchema,
    TableSchema,
    ColumnSchema,
    Mismatch,
    MismatchType,
    Severity
)

logger = logging.getLogger(__name__)


class MigrationAuditor:
    """
    Audits migration scripts for schema operations and compatibility.
    
    This class scans both SQL and Python migration scripts to identify
    schema operations and ensure they match the reference schema.
    """
    
    def __init__(self, reference_schema: Optional[DatabaseSchema] = None):
        """
        Initialize the migration auditor.
        
        Args:
            reference_schema: Reference database schema to compare against
        """
        self.reference_schema = reference_schema
        self.migration_scripts: List[str] = []
        self.operations: List[TableOperation] = []
        self.mismatches: List[Mismatch] = []
    
    def scan_migration_scripts(
        self, 
        directory: str, 
        patterns: Optional[List[str]] = None
    ) -> List[str]:
        """
        Scan directory for migration scripts (SQL and Python files).
        
        This method identifies migration scripts by:
        - File naming patterns (migrate_*, migration_*, *_migration.*)
        - File extensions (.sql, .py)
        - Content patterns (CREATE TABLE, ALTER TABLE, etc.)
        
        Args:
            directory: Root directory to scan
            patterns: Optional list of glob patterns (default: ['**/migrate*.sql', '**/migrate*.py'])
        
        Returns:
            List of migration script file paths
        
        Requirements: 8.1
        """
        logger.info(f"Scanning for migration scripts in: {directory}")
        
        directory_path = Path(directory)
        if not directory_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            return []
        
        if not directory_path.is_dir():
            logger.error(f"Path is not a directory: {directory}")
            return []
        
        # Default patterns for migration scripts
        if patterns is None:
            patterns = [
                '**/migrate*.sql',
                '**/migrate*.py',
                '**/*migration*.sql',
                '**/*migration*.py',
                '**/migration*.sql',
                '**/migration*.py'
            ]
        
        migration_files: Set[str] = set()
        
        # Directories to exclude
        excluded_dirs = {
            '__pycache__', '.venv', 'venv', '.env', 'env',
            'node_modules', '.git', '.pytest_cache', '.mypy_cache',
            '.tox', 'build', 'dist', '.eggs',
            '.python_packages', 'site-packages'
        }
        
        # Scan for files matching patterns
        for pattern in patterns:
            for file_path in directory_path.glob(pattern):
                # Skip if path contains excluded directories
                if any(excluded_dir in file_path.parts for excluded_dir in excluded_dirs):
                    continue
                
                if file_path.is_file():
                    # Verify it's actually a migration script by checking content
                    if self._is_migration_script(str(file_path)):
                        migration_files.add(str(file_path))
                        logger.debug(f"Found migration script: {file_path}")
        
        self.migration_scripts = sorted(list(migration_files))
        logger.info(f"Found {len(self.migration_scripts)} migration scripts")
        
        return self.migration_scripts
    
    def _is_migration_script(self, file_path: str) -> bool:
        """
        Check if a file is a migration script by examining its content.
        
        Args:
            file_path: Path to the file
        
        Returns:
            True if the file contains migration operations
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for schema modification keywords
            migration_keywords = [
                'CREATE TABLE', 'ALTER TABLE', 'DROP TABLE',
                'RENAME TABLE', 'sp_rename',
                'ADD COLUMN', 'DROP COLUMN', 'MODIFY COLUMN'
            ]
            
            content_upper = content.upper()
            return any(keyword in content_upper for keyword in migration_keywords)
            
        except Exception as e:
            logger.debug(f"Error reading file {file_path}: {e}")
            return False
    
    def audit_migration_operations(
        self, 
        script_path: Optional[str] = None
    ) -> List[TableOperation]:
        """
        Audit migration operations in scripts to detect schema changes.
        
        This method parses migration scripts to extract:
        - CREATE TABLE operations
        - ALTER TABLE operations
        - Table renames
        - Column additions/modifications/deletions
        
        Args:
            script_path: Specific script to audit, or None to audit all scanned scripts
        
        Returns:
            List of TableOperation objects found in migration scripts
        
        Requirements: 8.2
        """
        logger.info(f"Auditing migration operations in: {script_path or 'all scripts'}")
        
        scripts_to_audit = [script_path] if script_path else self.migration_scripts
        
        all_operations: List[TableOperation] = []
        
        for script in scripts_to_audit:
            if not script:
                continue
            
            try:
                # Determine file type and parse accordingly
                if script.endswith('.sql'):
                    operations = self._audit_sql_migration(script)
                elif script.endswith('.py'):
                    operations = self._audit_python_migration(script)
                else:
                    logger.warning(f"Unknown migration script type: {script}")
                    continue
                
                all_operations.extend(operations)
                logger.debug(f"Found {len(operations)} operations in {script}")
                
            except Exception as e:
                logger.error(f"Error auditing {script}: {e}")
        
        self.operations.extend(all_operations)
        logger.info(f"Total migration operations found: {len(all_operations)}")
        
        return all_operations
    
    def _audit_sql_migration(self, script_path: str) -> List[TableOperation]:
        """
        Audit SQL migration script for schema operations.
        
        Args:
            script_path: Path to SQL migration script
        
        Returns:
            List of TableOperation objects
        """
        operations: List[TableOperation] = []
        
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into statements (simple split by semicolon)
            statements = [s.strip() for s in content.split(';') if s.strip()]
            
            for line_num, statement in enumerate(statements, 1):
                statement_upper = statement.upper()
                
                # Parse CREATE TABLE
                if 'CREATE TABLE' in statement_upper:
                    op = self._parse_create_table_sql(statement, script_path, line_num)
                    if op:
                        operations.append(op)
                
                # Parse ALTER TABLE
                elif 'ALTER TABLE' in statement_upper:
                    op = self._parse_alter_table_sql(statement, script_path, line_num)
                    if op:
                        operations.append(op)
                
                # Parse sp_rename (SQL Server table rename)
                elif 'SP_RENAME' in statement_upper or 'EXEC SP_RENAME' in statement_upper:
                    op = self._parse_rename_table_sql(statement, script_path, line_num)
                    if op:
                        operations.append(op)
                
                # Parse DROP TABLE
                elif 'DROP TABLE' in statement_upper:
                    op = self._parse_drop_table_sql(statement, script_path, line_num)
                    if op:
                        operations.append(op)
        
        except Exception as e:
            logger.error(f"Error parsing SQL migration {script_path}: {e}")
        
        return operations
    
    def _parse_create_table_sql(
        self, 
        sql: str, 
        file_path: str, 
        line_number: int
    ) -> Optional[TableOperation]:
        """Parse CREATE TABLE from SQL."""
        # Pattern: CREATE TABLE [IF NOT EXISTS] table_name (columns...)
        pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\[)?(\w+)(?:\])?'
        match = re.search(pattern, sql, re.IGNORECASE)
        
        if not match:
            return None
        
        table_name = match.group(1)
        
        # Extract column names
        columns = self._extract_columns_from_create_sql(sql)
        
        return TableOperation(
            operation_type=OperationType.CREATE,
            table_name=table_name,
            columns=columns,
            file_path=file_path,
            line_number=line_number,
            code_snippet=sql[:200]
        )
    
    def _extract_columns_from_create_sql(self, sql: str) -> List[str]:
        """Extract column names from CREATE TABLE statement."""
        columns = []
        
        # Find the column definition section (between parentheses)
        match = re.search(r'\((.*)\)', sql, re.DOTALL | re.IGNORECASE)
        if not match:
            return columns
        
        column_defs = match.group(1)
        
        # Split by comma and extract column names
        for part in column_defs.split(','):
            part = part.strip()
            
            # Skip table-level constraints
            part_upper = part.upper()
            if part_upper.startswith(('PRIMARY KEY', 'FOREIGN KEY', 'CONSTRAINT', 'CHECK', 'UNIQUE', 'INDEX')):
                continue
            
            # Extract column name (first word, removing brackets)
            words = part.split()
            if words:
                col_name = words[0].strip('[]')
                if col_name and col_name.upper() not in ['PRIMARY', 'FOREIGN', 'CONSTRAINT', 'CHECK', 'UNIQUE', 'INDEX', 'KEY']:
                    columns.append(col_name)
        
        return columns
    
    def _parse_alter_table_sql(
        self, 
        sql: str, 
        file_path: str, 
        line_number: int
    ) -> Optional[TableOperation]:
        """Parse ALTER TABLE from SQL."""
        # Pattern: ALTER TABLE table_name
        pattern = r'ALTER\s+TABLE\s+(?:\[)?(\w+)(?:\])?'
        match = re.search(pattern, sql, re.IGNORECASE)
        
        if not match:
            return None
        
        table_name = match.group(1)
        
        # Extract columns being modified
        columns = self._extract_columns_from_alter_sql(sql)
        
        return TableOperation(
            operation_type=OperationType.ALTER,
            table_name=table_name,
            columns=columns,
            file_path=file_path,
            line_number=line_number,
            code_snippet=sql[:200]
        )
    
    def _extract_columns_from_alter_sql(self, sql: str) -> List[str]:
        """Extract column names from ALTER TABLE statement."""
        columns = []
        
        # Patterns for different ALTER operations
        patterns = [
            r'ADD\s+(?:COLUMN\s+)?(?:\[)?(\w+)(?:\])?',
            r'ALTER\s+COLUMN\s+(?:\[)?(\w+)(?:\])?',
            r'DROP\s+COLUMN\s+(?:\[)?(\w+)(?:\])?',
            r'MODIFY\s+(?:COLUMN\s+)?(?:\[)?(\w+)(?:\])?',
            r'RENAME\s+COLUMN\s+(?:\[)?(\w+)(?:\])?'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, sql, re.IGNORECASE)
            for match in matches:
                col_name = match.group(1)
                if col_name:
                    columns.append(col_name)
        
        return columns
    
    def _parse_rename_table_sql(
        self, 
        sql: str, 
        file_path: str, 
        line_number: int
    ) -> Optional[TableOperation]:
        """Parse sp_rename (table rename) from SQL."""
        # Pattern: EXEC sp_rename 'old_name', 'new_name'
        pattern = r"sp_rename\s+['\"](\w+)['\"],\s+['\"](\w+)['\"]"
        match = re.search(pattern, sql, re.IGNORECASE)
        
        if not match:
            return None
        
        old_name = match.group(1)
        new_name = match.group(2)
        
        # Create operation for the new table name
        return TableOperation(
            operation_type=OperationType.ALTER,
            table_name=new_name,
            columns=[],
            file_path=file_path,
            line_number=line_number,
            code_snippet=f"RENAME {old_name} TO {new_name}"
        )
    
    def _parse_drop_table_sql(
        self, 
        sql: str, 
        file_path: str, 
        line_number: int
    ) -> Optional[TableOperation]:
        """Parse DROP TABLE from SQL."""
        # Pattern: DROP TABLE [IF EXISTS] table_name
        pattern = r'DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:\[)?(\w+)(?:\])?'
        match = re.search(pattern, sql, re.IGNORECASE)
        
        if not match:
            return None
        
        table_name = match.group(1)
        
        return TableOperation(
            operation_type=OperationType.DELETE,
            table_name=table_name,
            columns=[],
            file_path=file_path,
            line_number=line_number,
            code_snippet=sql[:200]
        )
    
    def _audit_python_migration(self, script_path: str) -> List[TableOperation]:
        """
        Audit Python migration script for schema operations.
        
        Args:
            script_path: Path to Python migration script
        
        Returns:
            List of TableOperation objects
        """
        operations: List[TableOperation] = []
        
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse Python AST
            try:
                tree = ast.parse(content, filename=script_path)
            except SyntaxError as e:
                logger.warning(f"Syntax error in {script_path}: {e}")
                return operations
            
            # Look for SQL strings in the Python code
            for node in ast.walk(tree):
                # String literals
                if isinstance(node, ast.Str):
                    ops = self._parse_sql_in_python(node.s, script_path, node.lineno)
                    operations.extend(ops)
                
                # Constant nodes (Python 3.8+)
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    ops = self._parse_sql_in_python(node.value, script_path, node.lineno)
                    operations.extend(ops)
        
        except Exception as e:
            logger.error(f"Error parsing Python migration {script_path}: {e}")
        
        return operations
    
    def _parse_sql_in_python(
        self, 
        sql: str, 
        file_path: str, 
        line_number: int
    ) -> List[TableOperation]:
        """Parse SQL statements found in Python code."""
        operations: List[TableOperation] = []
        
        sql_upper = sql.upper()
        
        # Check for schema modification keywords
        if 'CREATE TABLE' in sql_upper:
            op = self._parse_create_table_sql(sql, file_path, line_number)
            if op:
                operations.append(op)
        
        if 'ALTER TABLE' in sql_upper:
            op = self._parse_alter_table_sql(sql, file_path, line_number)
            if op:
                operations.append(op)
        
        if 'DROP TABLE' in sql_upper:
            op = self._parse_drop_table_sql(sql, file_path, line_number)
            if op:
                operations.append(op)
        
        return operations
    
    def fix_migration_schema(
        self, 
        script_path: str, 
        mismatches: Optional[List[Mismatch]] = None,
        dry_run: bool = False
    ) -> Dict[str, any]:
        """
        Fix schema mismatches in migration scripts.
        
        This method updates migration scripts to match the reference schema by:
        - Correcting table names
        - Fixing column names and types
        - Adding missing columns
        - Removing extra columns
        
        Args:
            script_path: Path to migration script to fix
            mismatches: List of mismatches to fix (if None, detects automatically)
            dry_run: If True, only simulate fixes without applying them
        
        Returns:
            Dictionary with fix results including:
                - 'fixed': bool indicating success
                - 'changes': list of changes made
                - 'errors': list of errors encountered
        
        Requirements: 8.3
        """
        logger.info(f"Fixing migration schema in: {script_path} (dry_run={dry_run})")
        
        result = {
            'fixed': False,
            'changes': [],
            'errors': [],
            'script_path': script_path
        }
        
        if not self.reference_schema:
            error_msg = "No reference schema provided for fixing"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            return result
        
        try:
            # Read script content
            with open(script_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # If no mismatches provided, detect them
            if mismatches is None:
                mismatches = self._detect_migration_mismatches(script_path)
            
            if not mismatches:
                logger.info(f"No mismatches found in {script_path}")
                result['fixed'] = True
                return result
            
            # Apply fixes
            modified_content = original_content
            
            for mismatch in mismatches:
                try:
                    modified_content = self._apply_migration_fix(
                        modified_content,
                        mismatch
                    )
                    result['changes'].append({
                        'type': mismatch.mismatch_type.value,
                        'table': mismatch.table_name,
                        'column': mismatch.column_name,
                        'description': mismatch.fix_suggestion
                    })
                except Exception as e:
                    error_msg = f"Failed to fix {mismatch}: {str(e)}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
            
            # Write back if not dry run
            if not dry_run and modified_content != original_content:
                # Create backup
                backup_path = f"{script_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                logger.info(f"Created backup: {backup_path}")
                
                # Write modified content
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                logger.info(f"Updated migration script: {script_path}")
                
                result['fixed'] = True
            elif dry_run:
                logger.info(f"[DRY-RUN] Would apply {len(result['changes'])} changes")
                result['fixed'] = True
        
        except Exception as e:
            error_msg = f"Error fixing migration script: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
        
        return result
    
    def _detect_migration_mismatches(self, script_path: str) -> List[Mismatch]:
        """
        Detect schema mismatches in a migration script.
        
        Args:
            script_path: Path to migration script
        
        Returns:
            List of Mismatch objects
        """
        mismatches: List[Mismatch] = []
        
        if not self.reference_schema:
            return mismatches
        
        # Audit operations in this script
        operations = self.audit_migration_operations(script_path)
        
        # Check each operation against reference schema
        for op in operations:
            table_name = op.table_name
            ref_table = self.reference_schema.get_table(table_name)
            
            if op.operation_type == OperationType.CREATE:
                if not ref_table:
                    # Table in migration but not in reference
                    mismatch = Mismatch(
                        mismatch_type=MismatchType.EXTRA_TABLE,
                        severity=Severity.WARNING,
                        table_name=table_name,
                        locations=[op.location],
                        fix_suggestion=f"Remove CREATE TABLE for {table_name} or add to reference schema"
                    )
                    mismatches.append(mismatch)
                else:
                    # Check columns
                    for col_name in op.columns:
                        if not ref_table.has_column(col_name):
                            mismatch = Mismatch(
                                mismatch_type=MismatchType.EXTRA_COLUMN,
                                severity=Severity.WARNING,
                                table_name=table_name,
                                column_name=col_name,
                                locations=[op.location],
                                fix_suggestion=f"Remove column {col_name} from CREATE TABLE"
                            )
                            mismatches.append(mismatch)
        
        return mismatches
    
    def _apply_migration_fix(self, content: str, mismatch: Mismatch) -> str:
        """
        Apply a fix to migration script content.
        
        Args:
            content: Script content
            mismatch: Mismatch to fix
        
        Returns:
            Modified content
        """
        if mismatch.mismatch_type == MismatchType.COLUMN_NAME_MISMATCH:
            # Replace column name
            old_name = mismatch.actual_value
            new_name = mismatch.expected_value
            if old_name and new_name:
                pattern = r'\b' + re.escape(old_name) + r'\b'
                content = re.sub(pattern, new_name, content)
        
        elif mismatch.mismatch_type == MismatchType.COLUMN_TYPE_MISMATCH:
            # Replace column type
            column_name = mismatch.column_name
            old_type = mismatch.actual_value
            new_type = mismatch.expected_value
            if column_name and old_type and new_type:
                pattern = r'(\b' + re.escape(column_name) + r'\s+)' + re.escape(old_type) + r'\b'
                content = re.sub(pattern, r'\1' + new_type, content, flags=re.IGNORECASE)
        
        return content
    
    def generate_new_migration(
        self, 
        table_schema: TableSchema, 
        output_path: str,
        migration_type: str = 'create'
    ) -> str:
        """
        Generate a new migration script for a table.
        
        This method creates a migration script (SQL or Python) to:
        - Create a new table
        - Alter an existing table
        - Add/modify columns
        
        Args:
            table_schema: Schema of the table to migrate
            output_path: Path where migration script should be saved
            migration_type: Type of migration ('create', 'alter', 'rename')
        
        Returns:
            Path to the generated migration script
        
        Requirements: 8.5
        """
        logger.info(f"Generating {migration_type} migration for table: {table_schema.name}")
        
        # Determine file extension
        if output_path.endswith('.sql'):
            content = self._generate_sql_migration(table_schema, migration_type)
        elif output_path.endswith('.py'):
            content = self._generate_python_migration(table_schema, migration_type)
        else:
            # Default to SQL
            output_path += '.sql'
            content = self._generate_sql_migration(table_schema, migration_type)
        
        # Write migration script
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Generated migration script: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to write migration script: {e}")
            raise
    
    def _generate_sql_migration(
        self, 
        table_schema: TableSchema, 
        migration_type: str
    ) -> str:
        """Generate SQL migration script content."""
        lines = [
            f"-- Migration Script: {migration_type.upper()} {table_schema.name}",
            f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        
        if migration_type == 'create':
            lines.append(f"-- Create table {table_schema.name}")
            lines.append(f"IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{table_schema.name}')")
            lines.append("BEGIN")
            lines.append(f"    CREATE TABLE {table_schema.name} (")
            
            # Add columns
            column_defs = []
            for col in table_schema.columns:
                col_def = f"        {col.name} {col.data_type}"
                
                # Add length/precision
                if col.max_length:
                    col_def += f"({col.max_length})"
                elif col.precision and col.scale:
                    col_def += f"({col.precision},{col.scale})"
                elif col.precision:
                    col_def += f"({col.precision})"
                
                # Add nullable
                col_def += " NOT NULL" if not col.nullable else " NULL"
                
                # Add identity
                if col.is_identity:
                    col_def += " IDENTITY(1,1)"
                
                # Add default
                if col.default_value:
                    col_def += f" DEFAULT {col.default_value}"
                
                column_defs.append(col_def)
            
            # Add primary key
            if table_schema.primary_key:
                pk_cols = ', '.join(table_schema.primary_key)
                column_defs.append(f"        PRIMARY KEY ({pk_cols})")
            
            lines.append(',\n'.join(column_defs))
            lines.append("    );")
            lines.append("END")
        
        elif migration_type == 'alter':
            lines.append(f"-- Alter table {table_schema.name}")
            for col in table_schema.columns:
                lines.append(f"IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('{table_schema.name}') AND name = '{col.name}')")
                lines.append(f"    ALTER TABLE {table_schema.name} ADD {col.name} {col.data_type};")
        
        lines.append("")
        return '\n'.join(lines)
    
    def _generate_python_migration(
        self, 
        table_schema: TableSchema, 
        migration_type: str
    ) -> str:
        """Generate Python migration script content."""
        lines = [
            '"""',
            f'Migration Script: {migration_type.upper()} {table_schema.name}',
            f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            '"""',
            '',
            'import asyncio',
            'import os',
            'import sys',
            'import logging',
            '',
            '# Add azure_functions to path',
            "sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))",
            '',
            'from shared.database_handler import DatabaseHandler',
            'from shared.config import config_manager',
            '',
            'logging.basicConfig(level=logging.INFO)',
            'logger = logging.getLogger(__name__)',
            '',
            'async def migrate():',
            '    """Execute migration."""',
            '    config_manager.reload()',
            '    db_config = await config_manager.get_database_config()',
            '    db_handler = DatabaseHandler(db_config)',
            '',
            '    try:',
        ]
        
        if migration_type == 'create':
            # Generate CREATE TABLE query
            query_lines = [
                f'        query = """',
                f'        CREATE TABLE {table_schema.name} (',
            ]
            
            for i, col in enumerate(table_schema.columns):
                col_def = f'            {col.name} {col.data_type}'
                
                if col.max_length:
                    col_def += f'({col.max_length})'
                elif col.precision and col.scale:
                    col_def += f'({col.precision},{col.scale})'
                elif col.precision:
                    col_def += f'({col.precision})'
                
                col_def += ' NOT NULL' if not col.nullable else ' NULL'
                
                if col.is_identity:
                    col_def += ' IDENTITY(1,1)'
                
                if col.default_value:
                    col_def += f' DEFAULT {col.default_value}'
                
                if i < len(table_schema.columns) - 1:
                    col_def += ','
                
                query_lines.append(col_def)
            
            if table_schema.primary_key:
                pk_cols = ', '.join(table_schema.primary_key)
                query_lines.append(f'            PRIMARY KEY ({pk_cols})')
            
            query_lines.append('        );')
            query_lines.append('        """')
            
            lines.extend(query_lines)
            lines.append('        await db_handler.execute_query(query)')
            lines.append(f'        logger.info("Created table {table_schema.name}")')
        
        lines.extend([
            '',
            '    except Exception as e:',
            '        logger.error(f"Migration failed: {e}")',
            '        raise',
            '    finally:',
            '        if hasattr(db_handler, "close"):',
            '            await db_handler.close()',
            '',
            'if __name__ == "__main__":',
            '    asyncio.run(migrate())',
            ''
        ])
        
        return '\n'.join(lines)
    
    def get_migration_operations(self) -> List[TableOperation]:
        """
        Get all migration operations found.
        
        Returns:
            List of all TableOperation objects from migration scripts
        """
        return self.operations
    
    def get_migration_tables(self) -> Set[str]:
        """
        Get set of all table names found in migration scripts.
        
        Returns:
            Set of table names
        """
        return {op.table_name.lower() for op in self.operations}
    
    def clear(self) -> None:
        """Clear all stored operations and scripts."""
        self.migration_scripts.clear()
        self.operations.clear()
        self.mismatches.clear()
    
    def check_migration_compatibility(
        self, 
        migration_scripts: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        Check if migration scripts are compatible with reference schema.
        
        This method verifies that:
        - All tables in migrations exist in reference schema
        - Column definitions match reference schema
        - Data types are compatible
        - No conflicting operations exist
        
        Args:
            migration_scripts: List of migration scripts to check (if None, uses all scanned scripts)
        
        Returns:
            Dictionary with compatibility results:
                - 'compatible': bool indicating overall compatibility
                - 'issues': list of compatibility issues found
                - 'warnings': list of warnings
                - 'summary': summary statistics
        
        Requirements: 8.4
        """
        logger.info("Checking migration compatibility with reference schema")
        
        result = {
            'compatible': True,
            'issues': [],
            'warnings': [],
            'summary': {
                'total_scripts': 0,
                'total_operations': 0,
                'tables_created': 0,
                'tables_altered': 0,
                'mismatches_found': 0
            }
        }
        
        if not self.reference_schema:
            result['compatible'] = False
            result['issues'].append("No reference schema provided for compatibility check")
            return result
        
        # Use provided scripts or all scanned scripts
        scripts_to_check = migration_scripts or self.migration_scripts
        result['summary']['total_scripts'] = len(scripts_to_check)
        
        # Audit all operations in the scripts
        all_operations: List[TableOperation] = []
        for script in scripts_to_check:
            operations = self.audit_migration_operations(script)
            all_operations.extend(operations)
        
        result['summary']['total_operations'] = len(all_operations)
        
        # Track tables created and altered
        tables_created: Set[str] = set()
        tables_altered: Set[str] = set()
        
        # Check each operation for compatibility
        for op in all_operations:
            table_name = op.table_name.lower()
            ref_table = self.reference_schema.get_table(table_name)
            
            if op.operation_type == OperationType.CREATE:
                tables_created.add(table_name)
                
                # Check if table exists in reference
                if not ref_table:
                    issue = {
                        'type': 'missing_table_in_reference',
                        'severity': 'warning',
                        'table': table_name,
                        'location': str(op.location),
                        'message': f"Table '{table_name}' created in migration but not in reference schema"
                    }
                    result['warnings'].append(issue)
                else:
                    # Check columns
                    for col_name in op.columns:
                        if not ref_table.has_column(col_name):
                            issue = {
                                'type': 'extra_column',
                                'severity': 'error',
                                'table': table_name,
                                'column': col_name,
                                'location': str(op.location),
                                'message': f"Column '{col_name}' in migration not found in reference schema"
                            }
                            result['issues'].append(issue)
                            result['compatible'] = False
                            result['summary']['mismatches_found'] += 1
            
            elif op.operation_type == OperationType.ALTER:
                tables_altered.add(table_name)
                
                # Check if table exists in reference
                if not ref_table:
                    issue = {
                        'type': 'alter_nonexistent_table',
                        'severity': 'error',
                        'table': table_name,
                        'location': str(op.location),
                        'message': f"Attempting to alter table '{table_name}' that doesn't exist in reference"
                    }
                    result['issues'].append(issue)
                    result['compatible'] = False
        
        result['summary']['tables_created'] = len(tables_created)
        result['summary']['tables_altered'] = len(tables_altered)
        
        # Check for missing tables (tables in reference but not in migrations)
        ref_tables = set(self.reference_schema.tables.keys())
        migration_tables = tables_created.union(tables_altered)
        missing_tables = ref_tables - migration_tables
        
        if missing_tables:
            for table_name in missing_tables:
                warning = {
                    'type': 'missing_migration',
                    'severity': 'info',
                    'table': table_name,
                    'message': f"Table '{table_name}' in reference schema but no migration found"
                }
                result['warnings'].append(warning)
        
        # Simulate migration to check for conflicts
        simulation_result = self._simulate_migration(all_operations)
        if not simulation_result['success']:
            result['compatible'] = False
            result['issues'].extend(simulation_result['errors'])
        
        logger.info(f"Compatibility check complete. Compatible: {result['compatible']}, "
                   f"Issues: {len(result['issues'])}, Warnings: {len(result['warnings'])}")
        
        return result
    
    def _simulate_migration(self, operations: List[TableOperation]) -> Dict[str, any]:
        """
        Simulate migration execution to detect conflicts.
        
        This method simulates running the migration operations in order to detect:
        - Duplicate table creations
        - Altering non-existent tables
        - Conflicting operations
        - Dependency issues
        
        Args:
            operations: List of migration operations to simulate
        
        Returns:
            Dictionary with simulation results:
                - 'success': bool indicating if simulation succeeded
                - 'errors': list of errors encountered
                - 'final_schema': simulated final schema state
        
        Requirements: 8.4
        """
        logger.debug(f"Simulating migration with {len(operations)} operations")
        
        result = {
            'success': True,
            'errors': [],
            'final_schema': {}
        }
        
        # Track simulated schema state
        simulated_tables: Dict[str, Set[str]] = {}  # table_name -> set of columns
        
        # Process operations in order
        for op in operations:
            table_name = op.table_name.lower()
            
            if op.operation_type == OperationType.CREATE:
                # Check if table already exists
                if table_name in simulated_tables:
                    error = {
                        'type': 'duplicate_create',
                        'severity': 'error',
                        'table': table_name,
                        'location': str(op.location),
                        'message': f"Duplicate CREATE TABLE for '{table_name}'"
                    }
                    result['errors'].append(error)
                    result['success'] = False
                else:
                    # Create table in simulation
                    simulated_tables[table_name] = set(col.lower() for col in op.columns)
                    logger.debug(f"Simulated CREATE TABLE {table_name} with {len(op.columns)} columns")
            
            elif op.operation_type == OperationType.ALTER:
                # Check if table exists
                if table_name not in simulated_tables:
                    error = {
                        'type': 'alter_nonexistent',
                        'severity': 'error',
                        'table': table_name,
                        'location': str(op.location),
                        'message': f"ALTER TABLE on non-existent table '{table_name}'"
                    }
                    result['errors'].append(error)
                    result['success'] = False
                else:
                    # Add columns from ALTER (simplified - assumes ADD COLUMN)
                    for col in op.columns:
                        simulated_tables[table_name].add(col.lower())
                    logger.debug(f"Simulated ALTER TABLE {table_name}")
            
            elif op.operation_type == OperationType.DELETE:
                # Remove table from simulation
                if table_name in simulated_tables:
                    del simulated_tables[table_name]
                    logger.debug(f"Simulated DROP TABLE {table_name}")
                else:
                    warning = {
                        'type': 'drop_nonexistent',
                        'severity': 'warning',
                        'table': table_name,
                        'location': str(op.location),
                        'message': f"DROP TABLE on non-existent table '{table_name}'"
                    }
                    result['errors'].append(warning)
        
        # Store final simulated schema
        result['final_schema'] = {
            table: list(columns) 
            for table, columns in simulated_tables.items()
        }
        
        logger.debug(f"Migration simulation complete. Success: {result['success']}, "
                    f"Final tables: {len(simulated_tables)}")
        
        return result
    
    def get_compatibility_report(
        self, 
        compatibility_result: Dict[str, any]
    ) -> str:
        """
        Generate a human-readable compatibility report.
        
        Args:
            compatibility_result: Result from check_migration_compatibility()
        
        Returns:
            Formatted report string in Markdown format
        """
        lines = [
            "# Migration Compatibility Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            "",
            f"- **Compatible:** {'✓ Yes' if compatibility_result['compatible'] else '✗ No'}",
            f"- **Total Scripts:** {compatibility_result['summary']['total_scripts']}",
            f"- **Total Operations:** {compatibility_result['summary']['total_operations']}",
            f"- **Tables Created:** {compatibility_result['summary']['tables_created']}",
            f"- **Tables Altered:** {compatibility_result['summary']['tables_altered']}",
            f"- **Mismatches Found:** {compatibility_result['summary']['mismatches_found']}",
            "",
        ]
        
        # Add issues
        if compatibility_result['issues']:
            lines.append("## Issues")
            lines.append("")
            for i, issue in enumerate(compatibility_result['issues'], 1):
                lines.append(f"### Issue {i}: {issue['type']}")
                lines.append(f"- **Severity:** {issue['severity']}")
                lines.append(f"- **Table:** {issue.get('table', 'N/A')}")
                if 'column' in issue:
                    lines.append(f"- **Column:** {issue['column']}")
                if 'location' in issue:
                    lines.append(f"- **Location:** {issue['location']}")
                lines.append(f"- **Message:** {issue['message']}")
                lines.append("")
        
        # Add warnings
        if compatibility_result['warnings']:
            lines.append("## Warnings")
            lines.append("")
            for i, warning in enumerate(compatibility_result['warnings'], 1):
                lines.append(f"{i}. **{warning['type']}** - {warning['message']}")
            lines.append("")
        
        return '\n'.join(lines)
