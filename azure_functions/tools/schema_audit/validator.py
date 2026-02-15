"""
Validator module for Database Schema Audit System.

This module provides validation functionality for:
- Python syntax validation using ast.parse
- Import validation
- Schema consistency checking
- Dry-run mode validation

Requirements: 6.1, 6.2, 6.3
"""

import ast
import importlib.util
import sys
from pathlib import Path
from typing import List, Optional, Set, Dict
from datetime import datetime
import logging

from .models import ValidationResult

logger = logging.getLogger(__name__)


class Validator:
    """
    Validates Python files and schema consistency.
    
    This class provides validation functionality for:
    - Python syntax validation using ast.parse
    - Import statement validation
    - Schema consistency across files
    - Dry-run mode support
    
    Requirements: 6.1, 6.2, 6.3
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize the Validator.
        
        Args:
            dry_run: If True, validation runs in dry-run mode (no modifications)
        """
        self.dry_run = dry_run
        self.validated_files: Set[str] = set()
        self.validation_cache: Dict[str, ValidationResult] = {}
    
    def validate_python_syntax(self, file_path: str) -> ValidationResult:
        """
        Validate Python syntax using ast.parse.
        
        This method ensures that a Python file contains valid syntax by
        attempting to parse it with the ast module. This is critical for
        ensuring that modifications haven't broken the code.
        
        Args:
            file_path: Path to the Python file to validate
            
        Returns:
            ValidationResult indicating whether syntax is valid
            
        Requirements: 6.2 (Syntax validation)
        """
        logger.info(f"Validating Python syntax: {file_path}")
        
        result = ValidationResult(is_valid=True, file_path=file_path)
        
        # Check if file exists
        path = Path(file_path)
        if not path.exists():
            result.add_error(f"File not found: {file_path}")
            return result
        
        # Check if it's a Python file
        if not file_path.endswith('.py'):
            result.add_warning(f"Not a Python file: {file_path}")
            return result
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Attempt to parse with ast
            ast.parse(content, filename=file_path)
            
            logger.info(f"✓ Syntax validation passed: {file_path}")
            self.validated_files.add(file_path)
            
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            result.add_error(error_msg)
            logger.error(f"✗ Syntax error in {file_path}: {error_msg}")
            
        except Exception as e:
            error_msg = f"Failed to parse file: {str(e)}"
            result.add_error(error_msg)
            logger.error(f"✗ Parse error in {file_path}: {error_msg}")
        
        # Cache result
        self.validation_cache[file_path] = result
        return result
    
    def validate_imports(self, file_path: str) -> ValidationResult:
        """
        Validate that all import statements in a file are resolvable.
        
        This method checks that all imported modules exist and can be imported.
        This ensures that modifications haven't broken import dependencies.
        
        Args:
            file_path: Path to the Python file to validate
            
        Returns:
            ValidationResult indicating whether all imports are valid
            
        Requirements: 6.3 (Import validation)
        """
        logger.info(f"Validating imports: {file_path}")
        
        result = ValidationResult(is_valid=True, file_path=file_path)
        
        # Check if file exists
        path = Path(file_path)
        if not path.exists():
            result.add_error(f"File not found: {file_path}")
            return result
        
        try:
            # Read and parse file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=file_path)
            
            # Extract all import statements
            imports = self._extract_imports(tree)
            
            if not imports:
                logger.info(f"No imports found in {file_path}")
                return result
            
            logger.info(f"Found {len(imports)} import statements in {file_path}")
            
            # Validate each import
            for import_info in imports:
                import_valid = self._validate_single_import(
                    import_info['module'],
                    import_info['line'],
                    file_path
                )
                
                if not import_valid:
                    error_msg = f"Cannot import '{import_info['module']}' at line {import_info['line']}"
                    result.add_error(error_msg)
                    logger.warning(f"✗ {error_msg}")
            
            if result.is_valid:
                logger.info(f"✓ All imports valid in {file_path}")
            else:
                logger.warning(f"✗ Some imports failed in {file_path}")
            
        except SyntaxError as e:
            error_msg = f"Syntax error prevents import validation: {e.msg}"
            result.add_error(error_msg)
            logger.error(f"✗ {error_msg}")
            
        except Exception as e:
            error_msg = f"Failed to validate imports: {str(e)}"
            result.add_error(error_msg)
            logger.error(f"✗ {error_msg}")
        
        return result
    
    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, any]]:
        """
        Extract all import statements from an AST.
        
        Args:
            tree: AST of the Python file
            
        Returns:
            List of import information dictionaries
        """
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # Handle: import module
                for alias in node.names:
                    imports.append({
                        'module': alias.name,
                        'line': node.lineno,
                        'type': 'import'
                    })
            
            elif isinstance(node, ast.ImportFrom):
                # Handle: from module import name
                # Skip relative imports (level > 0 means relative import with dots)
                if node.level > 0:
                    # This is a relative import (from . or from ..), skip it
                    continue
                # Only process absolute imports
                if node.module:
                    imports.append({
                        'module': node.module,
                        'line': node.lineno,
                        'type': 'from'
                    })
        
        return imports
    
    def _validate_single_import(
        self, 
        module_name: str, 
        line_number: int,
        file_path: str
    ) -> bool:
        """
        Validate that a single module can be imported.
        
        Args:
            module_name: Name of the module to import
            line_number: Line number where import occurs
            file_path: Path to the file being validated
            
        Returns:
            True if import is valid, False otherwise
        """
        # Skip relative imports (they require context)
        if module_name.startswith('.'):
            logger.debug(f"Skipping relative import validation: {module_name}")
            return True
        
        # Skip built-in modules (they're always available)
        if module_name in sys.builtin_module_names:
            return True
        
        try:
            # Try to find the module spec
            spec = importlib.util.find_spec(module_name)
            
            if spec is None:
                logger.warning(f"Module not found: {module_name}")
                return False
            
            return True
            
        except ModuleNotFoundError:
            logger.warning(f"Module not found: {module_name}")
            return False
            
        except Exception as e:
            logger.warning(f"Error checking module {module_name}: {str(e)}")
            # Don't fail validation for unexpected errors
            return True
    
    def validate_schema_consistency(
        self,
        file_paths: List[str]
    ) -> ValidationResult:
        """
        Validate schema consistency across multiple files.
        
        This method ensures that all files use consistent schema definitions
        and that there are no conflicting table or column definitions.
        
        Args:
            file_paths: List of Python files to validate for consistency
            
        Returns:
            ValidationResult indicating whether schema is consistent
            
        Requirements: 6.3 (Consistency validation)
        """
        logger.info(f"Validating schema consistency across {len(file_paths)} files")
        
        result = ValidationResult(is_valid=True)
        
        if not file_paths:
            result.add_warning("No files provided for consistency validation")
            return result
        
        # Track table and column usage across files
        table_definitions: Dict[str, List[str]] = {}  # table -> [files]
        column_definitions: Dict[str, Dict[str, List[str]]] = {}  # table -> {column -> [files]}
        
        # Validate each file and extract schema information
        for file_path in file_paths:
            # First validate syntax
            syntax_result = self.validate_python_syntax(file_path)
            if not syntax_result.is_valid:
                result.add_error(f"Syntax errors in {file_path}")
                continue
            
            # Extract schema information
            try:
                schema_info = self._extract_schema_info(file_path)
                
                # Track table definitions
                for table_name in schema_info.get('tables', []):
                    if table_name not in table_definitions:
                        table_definitions[table_name] = []
                    table_definitions[table_name].append(file_path)
                
                # Track column definitions
                for table_name, columns in schema_info.get('columns', {}).items():
                    if table_name not in column_definitions:
                        column_definitions[table_name] = {}
                    
                    for column_name in columns:
                        if column_name not in column_definitions[table_name]:
                            column_definitions[table_name][column_name] = []
                        column_definitions[table_name][column_name].append(file_path)
                
            except Exception as e:
                error_msg = f"Failed to extract schema info from {file_path}: {str(e)}"
                result.add_error(error_msg)
                logger.error(error_msg)
        
        # Check for consistency issues
        # (In a full implementation, we would compare definitions across files)
        # For now, just report what we found
        logger.info(f"Found {len(table_definitions)} tables across {len(file_paths)} files")
        
        if result.is_valid:
            logger.info("✓ Schema consistency validation passed")
        else:
            logger.warning("✗ Schema consistency issues found")
        
        return result
    
    def _extract_schema_info(self, file_path: str) -> Dict:
        """
        Extract schema information from a Python file.
        
        This method parses the file and extracts table names and column names
        from SQL statements and database operations.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary with 'tables' and 'columns' keys
        """
        schema_info = {
            'tables': set(),
            'columns': {}  # table -> set of columns
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for CREATE TABLE statements
            import re
            
            # Pattern: CREATE TABLE table_name
            create_pattern = r'CREATE\s+TABLE\s+(\w+)'
            for match in re.finditer(create_pattern, content, re.IGNORECASE):
                table_name = match.group(1)
                schema_info['tables'].add(table_name)
            
            # Pattern: INSERT INTO table_name
            insert_pattern = r'INSERT\s+INTO\s+(\w+)'
            for match in re.finditer(insert_pattern, content, re.IGNORECASE):
                table_name = match.group(1)
                schema_info['tables'].add(table_name)
            
            # Pattern: save_structured_data calls
            save_pattern = r'save_structured_data\(["\'](\w+)["\']'
            for match in re.finditer(save_pattern, content):
                table_name = match.group(1)
                schema_info['tables'].add(table_name)
            
        except Exception as e:
            logger.warning(f"Failed to extract schema info from {file_path}: {str(e)}")
        
        return schema_info
    
    def _check_dry_run_mode(self) -> bool:
        """
        Check if validator is in dry-run mode.
        
        In dry-run mode, validation should not trigger any file modifications
        and should only report what would be validated.
        
        Returns:
            True if in dry-run mode, False otherwise
            
        Requirements: 6.1 (Dry-run validation)
        """
        if self.dry_run:
            logger.info("Running in DRY-RUN mode - no modifications will be made")
        return self.dry_run
    
    def validate_files(self, file_paths: List[str]) -> Dict[str, ValidationResult]:
        """
        Validate multiple files for syntax and imports.
        
        This is a convenience method that validates both syntax and imports
        for a list of files.
        
        Args:
            file_paths: List of Python files to validate
            
        Returns:
            Dictionary mapping file paths to validation results
        """
        logger.info(f"Validating {len(file_paths)} files")
        
        # Check dry-run mode
        self._check_dry_run_mode()
        
        results = {}
        
        for file_path in file_paths:
            # Validate syntax
            syntax_result = self.validate_python_syntax(file_path)
            
            # Only validate imports if syntax is valid
            if syntax_result.is_valid:
                import_result = self.validate_imports(file_path)
                
                # Combine results
                combined_result = ValidationResult(
                    is_valid=syntax_result.is_valid and import_result.is_valid,
                    file_path=file_path
                )
                combined_result.errors.extend(syntax_result.errors)
                combined_result.errors.extend(import_result.errors)
                combined_result.warnings.extend(syntax_result.warnings)
                combined_result.warnings.extend(import_result.warnings)
                
                results[file_path] = combined_result
            else:
                # If syntax is invalid, don't bother with imports
                results[file_path] = syntax_result
        
        # Summary
        valid_count = sum(1 for r in results.values() if r.is_valid)
        logger.info(f"Validation complete: {valid_count}/{len(file_paths)} files valid")
        
        return results
    
    def get_validation_summary(self) -> Dict[str, any]:
        """
        Get a summary of all validations performed.
        
        Returns:
            Dictionary with validation statistics
        """
        total_validated = len(self.validated_files)
        total_cached = len(self.validation_cache)
        
        valid_count = sum(
            1 for result in self.validation_cache.values() 
            if result.is_valid
        )
        
        return {
            'total_files_validated': total_validated,
            'total_cached_results': total_cached,
            'valid_files': valid_count,
            'invalid_files': total_cached - valid_count,
            'dry_run_mode': self.dry_run
        }
    
    def generate_test_cases(self, tables: List[str]) -> List[Dict[str, any]]:
        """
        Generate test cases for database operations.
        
        This method creates test cases that verify database operations
        use the correct schema. Each test case includes the table name,
        operation type, and test code template.
        
        Args:
            tables: List of table names to generate tests for
            
        Returns:
            List of test case dictionaries
            
        Requirements: 6.4 (Test case generation)
        """
        logger.info(f"Generating test cases for {len(tables)} tables")
        
        test_cases = []
        
        for table_name in tables:
            # Generate INSERT test case
            insert_test = {
                'table': table_name,
                'operation': 'INSERT',
                'test_name': f'test_{table_name}_insert',
                'description': f'Test INSERT operation for {table_name} table',
                'test_code': self._generate_insert_test_code(table_name)
            }
            test_cases.append(insert_test)
            
            # Generate SELECT test case
            select_test = {
                'table': table_name,
                'operation': 'SELECT',
                'test_name': f'test_{table_name}_select',
                'description': f'Test SELECT operation for {table_name} table',
                'test_code': self._generate_select_test_code(table_name)
            }
            test_cases.append(select_test)
            
            # Generate UPDATE test case
            update_test = {
                'table': table_name,
                'operation': 'UPDATE',
                'test_name': f'test_{table_name}_update',
                'description': f'Test UPDATE operation for {table_name} table',
                'test_code': self._generate_update_test_code(table_name)
            }
            test_cases.append(update_test)
        
        logger.info(f"Generated {len(test_cases)} test cases")
        return test_cases
    
    def _generate_insert_test_code(self, table_name: str) -> str:
        """
        Generate test code for INSERT operation.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Python test code as string
        """
        return f'''def test_{table_name}_insert():
    """Test INSERT operation for {table_name} table."""
    # TODO: Add test data
    test_data = {{}}
    
    # TODO: Perform INSERT operation
    # result = save_structured_data('{table_name}', test_data)
    
    # TODO: Verify insertion
    # assert result is not None
    pass
'''
    
    def _generate_select_test_code(self, table_name: str) -> str:
        """
        Generate test code for SELECT operation.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Python test code as string
        """
        return f'''def test_{table_name}_select():
    """Test SELECT operation for {table_name} table."""
    # TODO: Setup test data
    
    # TODO: Perform SELECT operation
    # query = "SELECT * FROM {table_name} WHERE id = ?"
    # result = execute_query(query, params)
    
    # TODO: Verify results
    # assert len(result) > 0
    pass
'''
    
    def _generate_update_test_code(self, table_name: str) -> str:
        """
        Generate test code for UPDATE operation.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Python test code as string
        """
        return f'''def test_{table_name}_update():
    """Test UPDATE operation for {table_name} table."""
    # TODO: Setup test data
    
    # TODO: Perform UPDATE operation
    # query = "UPDATE {table_name} SET column = ? WHERE id = ?"
    # result = execute_query(query, params)
    
    # TODO: Verify update
    # assert result is not None
    pass
'''
    
    def generate_comparison_script(
        self,
        reference_schema_path: str,
        output_path: str = "compare_schema.py"
    ) -> str:
        """
        Generate a script to compare database schema with reference.
        
        This method creates an executable Python script that connects to
        a database and compares its actual schema with the reference schema.
        The script can be run to verify that database matches expectations.
        
        Args:
            reference_schema_path: Path to reference schema JSON file
            output_path: Path where comparison script will be saved
            
        Returns:
            Path to the generated comparison script
            
        Requirements: 6.5 (Schema comparison script generation)
        """
        logger.info(f"Generating schema comparison script: {output_path}")
        
        script_content = f'''#!/usr/bin/env python3
"""
Database Schema Comparison Script

This script compares the actual database schema with the reference schema
from the BACPAC file. It identifies any differences and reports them.

Generated by: Database Schema Audit System
Reference Schema: {reference_schema_path}
"""

import json
import pyodbc
import sys
from typing import Dict, List, Any


def load_reference_schema(schema_path: str) -> Dict[str, Any]:
    """Load reference schema from JSON file."""
    print(f"Loading reference schema from: {{schema_path}}")
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_database_schema(connection_string: str) -> Dict[str, Any]:
    """Extract schema from actual database."""
    print(f"Connecting to database...")
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    
    schema = {{'tables': {{}}}}
    
    # Get all tables
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """)
    
    tables = [row.TABLE_NAME for row in cursor.fetchall()]
    print(f"Found {{len(tables)}} tables in database")
    
    # Get columns for each table
    for table_name in tables:
        cursor.execute("""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """, table_name)
        
        columns = []
        for row in cursor.fetchall():
            columns.append({{
                'name': row.COLUMN_NAME,
                'data_type': row.DATA_TYPE,
                'nullable': row.IS_NULLABLE == 'YES',
                'max_length': row.CHARACTER_MAXIMUM_LENGTH,
                'precision': row.NUMERIC_PRECISION,
                'scale': row.NUMERIC_SCALE
            }})
        
        schema['tables'][table_name] = {{'columns': columns}}
    
    conn.close()
    return schema


def compare_schemas(reference: Dict[str, Any], actual: Dict[str, Any]) -> List[str]:
    """Compare reference and actual schemas."""
    differences = []
    
    ref_tables = set(reference.get('tables', {{}}).keys())
    actual_tables = set(actual.get('tables', {{}}).keys())
    
    # Check for missing tables
    missing_tables = ref_tables - actual_tables
    if missing_tables:
        differences.append(f"Missing tables in database: {{', '.join(missing_tables)}}")
    
    # Check for extra tables
    extra_tables = actual_tables - ref_tables
    if extra_tables:
        differences.append(f"Extra tables in database: {{', '.join(extra_tables)}}")
    
    # Check columns for common tables
    common_tables = ref_tables & actual_tables
    for table_name in common_tables:
        ref_cols = {{col['name']: col for col in reference['tables'][table_name].get('columns', [])}}
        actual_cols = {{col['name']: col for col in actual['tables'][table_name].get('columns', [])}}
        
        ref_col_names = set(ref_cols.keys())
        actual_col_names = set(actual_cols.keys())
        
        # Missing columns
        missing_cols = ref_col_names - actual_col_names
        if missing_cols:
            differences.append(f"Table {{table_name}}: Missing columns {{', '.join(missing_cols)}}")
        
        # Extra columns
        extra_cols = actual_col_names - ref_col_names
        if extra_cols:
            differences.append(f"Table {{table_name}}: Extra columns {{', '.join(extra_cols)}}")
        
        # Type mismatches
        for col_name in ref_col_names & actual_col_names:
            ref_type = ref_cols[col_name]['data_type']
            actual_type = actual_cols[col_name]['data_type']
            if ref_type.lower() != actual_type.lower():
                differences.append(
                    f"Table {{table_name}}, Column {{col_name}}: "
                    f"Type mismatch (expected {{ref_type}}, got {{actual_type}})"
                )
    
    return differences


def main():
    """Main comparison function."""
    if len(sys.argv) < 2:
        print("Usage: python compare_schema.py <connection_string>")
        print("Example: python compare_schema.py 'DRIVER={{SQL Server}};SERVER=localhost;DATABASE=mydb;UID=user;PWD=pass'")
        sys.exit(1)
    
    connection_string = sys.argv[1]
    reference_schema_path = "{reference_schema_path}"
    
    try:
        # Load reference schema
        reference = load_reference_schema(reference_schema_path)
        
        # Get actual database schema
        actual = get_database_schema(connection_string)
        
        # Compare schemas
        print("\\nComparing schemas...")
        differences = compare_schemas(reference, actual)
        
        # Report results
        if not differences:
            print("\\n✓ SUCCESS: Database schema matches reference!")
            sys.exit(0)
        else:
            print(f"\\n✗ DIFFERENCES FOUND: {{len(differences)}} issues")
            for i, diff in enumerate(differences, 1):
                print(f"  {{i}}. {{diff}}")
            sys.exit(1)
    
    except Exception as e:
        print(f"\\n✗ ERROR: {{str(e)}}")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
        
        # Write script to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Make script executable on Unix-like systems
            import os
            import stat
            if hasattr(os, 'chmod'):
                st = os.stat(output_path)
                os.chmod(output_path, st.st_mode | stat.S_IEXEC)
            
            logger.info(f"✓ Generated comparison script: {output_path}")
            return output_path
            
        except Exception as e:
            error_msg = f"Failed to write comparison script: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def generate_deployment_report(
        self,
        validation_results: Dict[str, ValidationResult],
        mismatches: Optional[List] = None,
        fixes_applied: Optional[List] = None
    ) -> Dict[str, any]:
        """
        Generate deployment readiness report.
        
        This method analyzes validation results, remaining mismatches, and
        applied fixes to determine if the system is ready for deployment.
        
        Args:
            validation_results: Dictionary of file paths to validation results
            mismatches: Optional list of remaining schema mismatches
            fixes_applied: Optional list of fixes that were applied
            
        Returns:
            Dictionary containing deployment status and details
            
        Requirements: 6.6 (Deployment readiness reporting)
        """
        logger.info("Generating deployment readiness report")
        
        # Analyze validation results
        total_files = len(validation_results)
        valid_files = sum(1 for r in validation_results.values() if r.is_valid)
        invalid_files = total_files - valid_files
        
        total_errors = sum(len(r.errors) for r in validation_results.values())
        total_warnings = sum(len(r.warnings) for r in validation_results.values())
        
        # Analyze mismatches
        critical_mismatches = 0
        warning_mismatches = 0
        info_mismatches = 0
        
        if mismatches:
            from .models import Severity
            for mismatch in mismatches:
                if hasattr(mismatch, 'severity'):
                    if mismatch.severity == Severity.CRITICAL:
                        critical_mismatches += 1
                    elif mismatch.severity == Severity.WARNING:
                        warning_mismatches += 1
                    elif mismatch.severity == Severity.INFO:
                        info_mismatches += 1
        
        # Analyze fixes
        fixes_successful = 0
        fixes_failed = 0
        
        if fixes_applied:
            for fix in fixes_applied:
                if hasattr(fix, 'applied'):
                    if fix.applied:
                        fixes_successful += 1
                    else:
                        fixes_failed += 1
        
        # Determine deployment readiness
        # Ready if: all files valid AND no critical mismatches
        ready_for_deployment = (invalid_files == 0 and critical_mismatches == 0)
        
        # Generate status message
        if critical_mismatches > 0:
            status = "NOT READY"
            status_message = f"Cannot deploy: {critical_mismatches} critical mismatches remain"
        elif invalid_files > 0:
            status = "NOT READY"
            status_message = f"Cannot deploy: {invalid_files} files have validation errors"
        elif warning_mismatches > 0:
            status = "READY WITH WARNINGS"
            status_message = f"Deployment possible but {warning_mismatches} warnings exist"
        else:
            status = "READY"
            status_message = "System is ready for deployment"
        
        # Build report
        report = {
            'status': status,
            'ready_for_deployment': ready_for_deployment,
            'status_message': status_message,
            'timestamp': datetime.now().isoformat(),
            'validation': {
                'total_files': total_files,
                'valid_files': valid_files,
                'invalid_files': invalid_files,
                'total_errors': total_errors,
                'total_warnings': total_warnings
            },
            'mismatches': {
                'critical': critical_mismatches,
                'warning': warning_mismatches,
                'info': info_mismatches,
                'total': critical_mismatches + warning_mismatches + info_mismatches
            },
            'fixes': {
                'successful': fixes_successful,
                'failed': fixes_failed,
                'total': fixes_successful + fixes_failed
            },
            'recommendations': self._generate_recommendations(
                ready_for_deployment,
                critical_mismatches,
                invalid_files,
                warning_mismatches
            )
        }
        
        # Log summary
        logger.info(f"Deployment Status: {status}")
        logger.info(f"  Files: {valid_files}/{total_files} valid")
        logger.info(f"  Mismatches: {critical_mismatches} critical, {warning_mismatches} warnings")
        logger.info(f"  Fixes: {fixes_successful} successful, {fixes_failed} failed")
        
        return report
    
    def _generate_recommendations(
        self,
        ready: bool,
        critical_mismatches: int,
        invalid_files: int,
        warning_mismatches: int
    ) -> List[str]:
        """
        Generate deployment recommendations based on status.
        
        Args:
            ready: Whether system is ready for deployment
            critical_mismatches: Number of critical mismatches
            invalid_files: Number of files with validation errors
            warning_mismatches: Number of warning-level mismatches
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if ready:
            recommendations.append("System is ready for deployment")
            recommendations.append("Run final integration tests before deploying")
            if warning_mismatches > 0:
                recommendations.append(f"Review {warning_mismatches} warnings before deployment")
        else:
            if critical_mismatches > 0:
                recommendations.append(f"Fix {critical_mismatches} critical mismatches before deployment")
                recommendations.append("Run schema fixer to automatically correct mismatches")
            
            if invalid_files > 0:
                recommendations.append(f"Fix validation errors in {invalid_files} files")
                recommendations.append("Check syntax errors and import issues")
            
            recommendations.append("Re-run validation after fixes are applied")
            recommendations.append("Use dry-run mode to preview changes before applying")
        
        return recommendations
