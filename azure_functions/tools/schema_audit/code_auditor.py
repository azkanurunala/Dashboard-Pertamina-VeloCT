"""
Code Auditor for Database Schema Audit System.

This module scans Python code to identify database operations including:
- CREATE TABLE statements
- INSERT operations
- save_structured_data calls
- Other database operations

Requirements: 2.1, 2.2
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Optional, Set
import logging

from azure_functions.tools.schema_audit.models import (
    TableOperation, 
    CodeLocation, 
    OperationType
)

logger = logging.getLogger(__name__)


class CodeAuditor:
    """
    Audits Python code to find database operations.
    
    This class scans directories for Python files and extracts information about
    database operations including table names, columns, and operation types.
    """
    
    def __init__(self):
        """Initialize the code auditor."""
        self.operations: List[TableOperation] = []
        self.scanned_files: Set[str] = set()
    
    def scan_directory(self, directory: str, patterns: Optional[List[str]] = None) -> List[CodeLocation]:
        """
        Scan directory recursively for Python files containing database operations.
        
        Args:
            directory: Root directory to scan
            patterns: Optional list of glob patterns to match (e.g., ['*.py'])
        
        Returns:
            List of CodeLocation objects where database operations were found
        
        Requirements: 2.1
        """
        logger.info(f"Scanning directory: {directory}")
        
        directory_path = Path(directory)
        if not directory_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            return []
        
        if not directory_path.is_dir():
            logger.error(f"Path is not a directory: {directory}")
            return []
        
        locations: List[CodeLocation] = []
        
        # Default to scanning all Python files
        if patterns is None:
            patterns = ['**/*.py']
        
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
                
                if self._is_python_file(str(file_path)):
                    try:
                        file_locations = self._scan_file(str(file_path))
                        locations.extend(file_locations)
                        self.scanned_files.add(str(file_path))
                    except Exception as e:
                        logger.warning(f"Error scanning file {file_path}: {e}")
        
        logger.info(f"Scanned {len(self.scanned_files)} files, found {len(locations)} operation locations")
        return locations
    
    def _is_python_file(self, file_path: str) -> bool:
        """
        Check if a file is a Python file.
        
        Args:
            file_path: Path to the file
        
        Returns:
            True if the file is a Python file, False otherwise
        
        Requirements: 2.1
        """
        path = Path(file_path)
        
        # Check extension
        if path.suffix != '.py':
            return False
        
        # Skip common directories that should be excluded
        excluded_dirs = {
            '__pycache__', '.venv', 'venv', '.env', 'env',
            'node_modules', '.git', '.pytest_cache', '.mypy_cache',
            '.tox', 'build', 'dist', '.eggs', '*.egg-info',
            '.python_packages', 'site-packages'
        }
        
        # Check if any part of the path matches excluded directories
        for part in path.parts:
            if part in excluded_dirs or part.startswith('.') and part != '.':
                return False
        
        # Skip if file doesn't exist or is not a file
        if not path.exists() or not path.is_file():
            return False
        
        return True
    
    def _scan_file(self, file_path: str) -> List[CodeLocation]:
        """
        Scan a single Python file for database operations.
        
        Args:
            file_path: Path to the Python file
        
        Returns:
            List of CodeLocation objects where operations were found
        """
        locations: List[CodeLocation] = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract operations from this file
            operations = self.extract_table_operations(file_path)
            
            # Convert operations to locations
            for op in operations:
                locations.append(op.location)
            
        except Exception as e:
            logger.warning(f"Error reading file {file_path}: {e}")
        
        return locations
    
    def extract_table_operations(self, file_path: str) -> List[TableOperation]:
        """
        Extract database table operations from a Python file using AST parsing.
        
        Args:
            file_path: Path to the Python file
        
        Returns:
            List of TableOperation objects found in the file
        
        Requirements: 2.2
        """
        operations: List[TableOperation] = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the Python file into an AST
            try:
                tree = ast.parse(content, filename=file_path)
            except SyntaxError as e:
                logger.warning(f"Syntax error in {file_path}: {e}")
                return operations
            
            # Walk the AST to find database operations
            for node in ast.walk(tree):
                # Look for string literals that might contain SQL
                if isinstance(node, ast.Str):
                    sql_operations = self._parse_sql_statement(node.s, file_path, node.lineno)
                    operations.extend(sql_operations)
                
                # Look for f-strings and formatted strings
                elif isinstance(node, ast.JoinedStr):
                    # Extract the string parts
                    sql_str = self._extract_fstring_content(node)
                    if sql_str:
                        sql_operations = self._parse_sql_statement(sql_str, file_path, node.lineno)
                        operations.extend(sql_operations)
                
                # Look for Constant nodes (Python 3.8+)
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    sql_operations = self._parse_sql_statement(node.value, file_path, node.lineno)
                    operations.extend(sql_operations)
            
            # Also detect save_structured_data calls
            save_data_operations = self.parse_save_structured_data_calls(file_path)
            operations.extend(save_data_operations)
            
            # Store operations for this file
            self.operations.extend(operations)
            
        except Exception as e:
            logger.error(f"Error extracting operations from {file_path}: {e}")
        
        return operations
    
    def _extract_fstring_content(self, node: ast.JoinedStr) -> str:
        """
        Extract content from an f-string node.
        
        Args:
            node: AST JoinedStr node
        
        Returns:
            String content with placeholders for formatted values
        """
        parts = []
        for value in node.values:
            if isinstance(value, ast.Str):
                parts.append(value.s)
            elif isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                # For formatted values, use a placeholder
                parts.append("{}")
        return ''.join(parts)
    
    def _parse_sql_statement(self, sql: str, file_path: str, line_number: int) -> List[TableOperation]:
        """
        Parse a SQL statement to extract table operations.
        
        Args:
            sql: SQL statement string
            file_path: Path to the file containing the SQL
            line_number: Line number where the SQL appears
        
        Returns:
            List of TableOperation objects extracted from the SQL
        
        Requirements: 2.2
        """
        operations: List[TableOperation] = []
        
        # Normalize SQL for parsing
        sql_upper = sql.upper().strip()
        
        # Skip if not a SQL statement
        if not any(keyword in sql_upper for keyword in ['CREATE', 'INSERT', 'UPDATE', 'DELETE', 'SELECT', 'ALTER']):
            return operations
        
        try:
            # Parse CREATE TABLE statements
            if 'CREATE TABLE' in sql_upper:
                op = self._parse_create_table(sql, file_path, line_number)
                if op:
                    operations.append(op)
            
            # Parse INSERT statements
            elif 'INSERT INTO' in sql_upper:
                op = self._parse_insert_statement(sql, file_path, line_number)
                if op:
                    operations.append(op)
            
            # Parse UPDATE statements
            elif 'UPDATE' in sql_upper and 'SET' in sql_upper:
                op = self._parse_update_statement(sql, file_path, line_number)
                if op:
                    operations.append(op)
            
            # Parse DELETE statements
            elif 'DELETE FROM' in sql_upper:
                op = self._parse_delete_statement(sql, file_path, line_number)
                if op:
                    operations.append(op)
            
            # Parse SELECT statements
            elif 'SELECT' in sql_upper and 'FROM' in sql_upper:
                op = self._parse_select_statement(sql, file_path, line_number)
                if op:
                    operations.append(op)
            
            # Parse ALTER TABLE statements
            elif 'ALTER TABLE' in sql_upper:
                op = self._parse_alter_table(sql, file_path, line_number)
                if op:
                    operations.append(op)
        
        except Exception as e:
            logger.debug(f"Error parsing SQL at {file_path}:{line_number}: {e}")
        
        return operations
    
    def _parse_create_table(self, sql: str, file_path: str, line_number: int) -> Optional[TableOperation]:
        """Parse CREATE TABLE statement."""
        # Pattern: CREATE TABLE [IF NOT EXISTS] table_name (columns...)
        pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\[)?(\w+)(?:\])?'
        match = re.search(pattern, sql, re.IGNORECASE)
        
        if not match:
            return None
        
        table_name = match.group(1)
        
        # Extract column names from the CREATE TABLE statement
        columns = self._extract_columns_from_create(sql)
        
        return TableOperation(
            operation_type=OperationType.CREATE,
            table_name=table_name,
            columns=columns,
            file_path=file_path,
            line_number=line_number,
            code_snippet=sql[:200]  # First 200 chars
        )
    
    def _extract_columns_from_create(self, sql: str) -> List[str]:
        """Extract column names from CREATE TABLE statement."""
        columns = []
        
        # Find the column definition section (between parentheses)
        match = re.search(r'\((.*)\)', sql, re.DOTALL | re.IGNORECASE)
        if not match:
            return columns
        
        column_defs = match.group(1)
        
        # Split by comma and extract column names
        # This is a simplified parser - may not handle all edge cases
        for part in column_defs.split(','):
            part = part.strip()
            
            # Skip standalone table-level constraints (those that start with constraint keywords)
            part_upper = part.upper()
            if part_upper.startswith(('PRIMARY KEY (', 'FOREIGN KEY (', 'CONSTRAINT ', 'CHECK (', 'UNIQUE (')):
                continue
            
            # Extract column name (first word, removing brackets)
            words = part.split()
            if words:
                col_name = words[0].strip('[]')
                # Check if this is a column definition (not a constraint keyword)
                if col_name and col_name.upper() not in ['PRIMARY', 'FOREIGN', 'CONSTRAINT', 'CHECK', 'UNIQUE', 'INDEX', 'KEY']:
                    columns.append(col_name)
        
        return columns
    
    def _parse_insert_statement(self, sql: str, file_path: str, line_number: int) -> Optional[TableOperation]:
        """Parse INSERT INTO statement."""
        # Pattern: INSERT INTO table_name (columns...) VALUES (...)
        pattern = r'INSERT\s+INTO\s+(?:\[)?(\w+)(?:\])?'
        match = re.search(pattern, sql, re.IGNORECASE)
        
        if not match:
            return None
        
        table_name = match.group(1)
        
        # Extract column names if specified
        columns = self._extract_columns_from_insert(sql)
        
        return TableOperation(
            operation_type=OperationType.INSERT,
            table_name=table_name,
            columns=columns,
            file_path=file_path,
            line_number=line_number,
            code_snippet=sql[:200]
        )
    
    def _extract_columns_from_insert(self, sql: str) -> List[str]:
        """Extract column names from INSERT statement."""
        columns = []
        
        # Pattern: INSERT INTO table (col1, col2, col3)
        pattern = r'INSERT\s+INTO\s+\w+\s*\((.*?)\)\s*VALUES'
        match = re.search(pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if match:
            column_list = match.group(1)
            # Split by comma and clean up
            for col in column_list.split(','):
                col_name = col.strip().strip('[]')
                if col_name:
                    columns.append(col_name)
        
        return columns
    
    def _parse_update_statement(self, sql: str, file_path: str, line_number: int) -> Optional[TableOperation]:
        """Parse UPDATE statement."""
        # Pattern: UPDATE table_name SET col1=val1, col2=val2
        pattern = r'UPDATE\s+(?:\[)?(\w+)(?:\])?'
        match = re.search(pattern, sql, re.IGNORECASE)
        
        if not match:
            return None
        
        table_name = match.group(1)
        
        # Extract column names from SET clause
        columns = self._extract_columns_from_update(sql)
        
        return TableOperation(
            operation_type=OperationType.UPDATE,
            table_name=table_name,
            columns=columns,
            file_path=file_path,
            line_number=line_number,
            code_snippet=sql[:200]
        )
    
    def _extract_columns_from_update(self, sql: str) -> List[str]:
        """Extract column names from UPDATE statement."""
        columns = []
        
        # Pattern: SET col1=val1, col2=val2
        pattern = r'SET\s+(.*?)(?:WHERE|$)'
        match = re.search(pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if match:
            set_clause = match.group(1)
            # Split by comma and extract column names
            for assignment in set_clause.split(','):
                if '=' in assignment:
                    col_name = assignment.split('=')[0].strip().strip('[]')
                    if col_name:
                        columns.append(col_name)
        
        return columns
    
    def _parse_delete_statement(self, sql: str, file_path: str, line_number: int) -> Optional[TableOperation]:
        """Parse DELETE FROM statement."""
        # Pattern: DELETE FROM table_name
        pattern = r'DELETE\s+FROM\s+(?:\[)?(\w+)(?:\])?'
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
    
    def _parse_select_statement(self, sql: str, file_path: str, line_number: int) -> Optional[TableOperation]:
        """Parse SELECT statement."""
        # Pattern: SELECT ... FROM table_name
        pattern = r'FROM\s+(?:\[)?(\w+)(?:\])?'
        match = re.search(pattern, sql, re.IGNORECASE)
        
        if not match:
            return None
        
        table_name = match.group(1)
        
        # Extract selected columns
        columns = self._extract_columns_from_select(sql)
        
        return TableOperation(
            operation_type=OperationType.SELECT,
            table_name=table_name,
            columns=columns,
            file_path=file_path,
            line_number=line_number,
            code_snippet=sql[:200]
        )
    
    def _extract_columns_from_select(self, sql: str) -> List[str]:
        """Extract column names from SELECT statement."""
        columns = []
        
        # Pattern: SELECT col1, col2, col3 FROM
        pattern = r'SELECT\s+(.*?)\s+FROM'
        match = re.search(pattern, sql, re.IGNORECASE | re.DOTALL)
        
        if match:
            select_clause = match.group(1).strip()
            # Skip SELECT *
            if select_clause == '*':
                return columns
            # Split by comma and extract column names
            for col in select_clause.split(','):
                col_name = col.strip().strip('[]')
                # Handle aliases (col AS alias)
                if ' AS ' in col_name.upper():
                    col_name = col_name.split()[0]
                if col_name and col_name != '*':
                    columns.append(col_name)
        
        return columns
    
    def _parse_alter_table(self, sql: str, file_path: str, line_number: int) -> Optional[TableOperation]:
        """Parse ALTER TABLE statement."""
        # Pattern: ALTER TABLE table_name
        pattern = r'ALTER\s+TABLE\s+(?:\[)?(\w+)(?:\])?'
        match = re.search(pattern, sql, re.IGNORECASE)
        
        if not match:
            return None
        
        table_name = match.group(1)
        
        # Extract column names if adding/modifying columns
        columns = self._extract_columns_from_alter(sql)
        
        return TableOperation(
            operation_type=OperationType.ALTER,
            table_name=table_name,
            columns=columns,
            file_path=file_path,
            line_number=line_number,
            code_snippet=sql[:200]
        )
    
    def _extract_columns_from_alter(self, sql: str) -> List[str]:
        """Extract column names from ALTER TABLE statement."""
        columns = []
        
        # Pattern: ADD COLUMN col_name or ALTER COLUMN col_name
        patterns = [
            r'ADD\s+(?:COLUMN\s+)?(?:\[)?(\w+)(?:\])?',
            r'ALTER\s+COLUMN\s+(?:\[)?(\w+)(?:\])?',
            r'DROP\s+COLUMN\s+(?:\[)?(\w+)(?:\])?',
            r'MODIFY\s+(?:COLUMN\s+)?(?:\[)?(\w+)(?:\])?'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, sql, re.IGNORECASE)
            for match in matches:
                col_name = match.group(1)
                if col_name:
                    columns.append(col_name)
        
        return columns
    
    def parse_save_structured_data_calls(self, file_path: str) -> List[TableOperation]:
        """
        Parse save_structured_data function calls to extract table operations.
        
        This method detects calls to save_structured_data(table_name, data) and
        extracts the table name parameter.
        
        Args:
            file_path: Path to the Python file
        
        Returns:
            List of TableOperation objects for save_structured_data calls
        
        Requirements: 2.3, 2.4, 2.5
        """
        operations: List[TableOperation] = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the Python file into an AST
            try:
                tree = ast.parse(content, filename=file_path)
            except SyntaxError as e:
                logger.warning(f"Syntax error in {file_path}: {e}")
                return operations
            
            # Walk the AST to find function calls
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check if this is a save_structured_data call
                    func_name = self._get_function_name(node.func)
                    
                    if func_name == 'save_structured_data':
                        # Extract table name from first argument
                        table_name = self._extract_table_name_from_call(node)
                        
                        if table_name:
                            # Get code snippet for context
                            code_snippet = self._get_code_snippet(content, node.lineno)
                            
                            operation = TableOperation(
                                operation_type=OperationType.INSERT,  # save_structured_data is an INSERT operation
                                table_name=table_name,
                                columns=[],  # Columns are determined at runtime from data dict
                                file_path=file_path,
                                line_number=node.lineno,
                                code_snippet=code_snippet
                            )
                            operations.append(operation)
                            logger.debug(f"Found save_structured_data call for table '{table_name}' at {file_path}:{node.lineno}")
            
            # Note: We don't add to self.operations here because this method is called
            # from extract_table_operations which handles that
        
        except Exception as e:
            logger.error(f"Error parsing save_structured_data calls from {file_path}: {e}")
        
        return operations
    
    def _get_function_name(self, node: ast.AST) -> str:
        """
        Extract function name from a Call node.
        
        Handles both simple calls (func()) and attribute calls (obj.func()).
        
        Args:
            node: AST node representing the function being called
        
        Returns:
            Function name as string
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ""
    
    def _extract_table_name_from_call(self, call_node: ast.Call) -> Optional[str]:
        """
        Extract table name from save_structured_data call arguments.
        
        The function signature is: save_structured_data(table_name: str, data: List[Dict])
        We extract the first argument which is the table name.
        
        Args:
            call_node: AST Call node
        
        Returns:
            Table name as string, or None if not extractable
        """
        # Check if there are arguments
        if not call_node.args or len(call_node.args) < 1:
            return None
        
        # Get the first argument (table_name)
        first_arg = call_node.args[0]
        
        # Handle string literals
        if isinstance(first_arg, ast.Str):
            return first_arg.s
        elif isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            return first_arg.value
        
        # Handle variables (we can't determine the value at static analysis time)
        elif isinstance(first_arg, ast.Name):
            # Return a placeholder indicating it's a variable
            return f"<variable:{first_arg.id}>"
        
        # Handle f-strings or other complex expressions
        elif isinstance(first_arg, ast.JoinedStr):
            # Try to extract static parts
            return self._extract_fstring_content(first_arg)
        
        return None
    
    def _get_code_snippet(self, content: str, line_number: int, context_lines: int = 2) -> str:
        """
        Extract a code snippet around a specific line number.
        
        Args:
            content: Full file content
            line_number: Line number to extract (1-indexed)
            context_lines: Number of lines before and after to include
        
        Returns:
            Code snippet as string
        """
        lines = content.split('\n')
        
        # Convert to 0-indexed
        line_idx = line_number - 1
        
        # Calculate range
        start_idx = max(0, line_idx - context_lines)
        end_idx = min(len(lines), line_idx + context_lines + 1)
        
        # Extract snippet
        snippet_lines = lines[start_idx:end_idx]
        snippet = '\n'.join(snippet_lines)
        
        # Limit length
        if len(snippet) > 200:
            snippet = snippet[:200] + "..."
        
        return snippet
    
    def _detect_create_table(self, sql: str, file_path: str, line_number: int) -> Optional[TableOperation]:
        """
        Detect CREATE TABLE operations in SQL statements.
        
        This is an alias for _parse_create_table for consistency with task naming.
        
        Args:
            sql: SQL statement
            file_path: Path to file containing the SQL
            line_number: Line number in the file
        
        Returns:
            TableOperation if CREATE TABLE found, None otherwise
        
        Requirements: 2.3
        """
        return self._parse_create_table(sql, file_path, line_number)
    
    def _detect_insert_operations(self, sql: str, file_path: str, line_number: int) -> Optional[TableOperation]:
        """
        Detect INSERT operations in SQL statements.
        
        This is an alias for _parse_insert_statement for consistency with task naming.
        
        Args:
            sql: SQL statement
            file_path: Path to file containing the SQL
            line_number: Line number in the file
        
        Returns:
            TableOperation if INSERT found, None otherwise
        
        Requirements: 2.4
        """
        return self._parse_insert_statement(sql, file_path, line_number)
    
    def _detect_save_structured_data(self, file_path: str) -> List[TableOperation]:
        """
        Detect save_structured_data function calls.
        
        This is an alias for parse_save_structured_data_calls for consistency with task naming.
        
        Args:
            file_path: Path to the Python file
        
        Returns:
            List of TableOperation objects for save_structured_data calls
        
        Requirements: 2.5
        """
        return self.parse_save_structured_data_calls(file_path)
    
    def build_operation_map(self) -> Dict[str, List[TableOperation]]:
        """
        Build a map of table names to their operations.
        
        Returns:
            Dictionary mapping table names to lists of operations
        
        Requirements: 2.6
        """
        operation_map: Dict[str, List[TableOperation]] = {}
        
        for operation in self.operations:
            table_name = operation.table_name.lower()
            if table_name not in operation_map:
                operation_map[table_name] = []
            operation_map[table_name].append(operation)
        
        return operation_map
    
    def get_operations_by_table(self, table_name: str) -> List[TableOperation]:
        """
        Get all operations for a specific table.
        
        Args:
            table_name: Name of the table
        
        Returns:
            List of operations for the table
        """
        return [op for op in self.operations if op.table_name.lower() == table_name.lower()]
    
    def get_operations_by_type(self, operation_type: OperationType) -> List[TableOperation]:
        """
        Get all operations of a specific type.
        
        Args:
            operation_type: Type of operation to filter by
        
        Returns:
            List of operations of the specified type
        """
        return [op for op in self.operations if op.operation_type == operation_type]
    
    def get_tables(self) -> Set[str]:
        """
        Get set of all table names found in operations.
        
        Returns:
            Set of table names
        """
        return {op.table_name.lower() for op in self.operations}
    
    def clear(self) -> None:
        """Clear all stored operations and scanned files."""
        self.operations.clear()
        self.scanned_files.clear()
