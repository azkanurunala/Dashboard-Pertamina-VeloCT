"""
Unit tests for CodeAuditor class.

Tests basic functionality of code auditing including:
- File scanning
- SQL statement parsing
- Operation extraction
"""

import ast
import pytest
import tempfile
import os
from pathlib import Path

from azure_functions.tools.schema_audit.code_auditor import CodeAuditor
from azure_functions.tools.schema_audit.models import OperationType


class TestCodeAuditor:
    """Test suite for CodeAuditor class."""
    
    def test_is_python_file(self):
        """Test Python file detection."""
        auditor = CodeAuditor()
        
        # Create temporary files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a Python file
            py_file = Path(tmpdir) / "test.py"
            py_file.write_text("print('hello')")
            
            # Create a non-Python file
            txt_file = Path(tmpdir) / "test.txt"
            txt_file.write_text("hello")
            
            assert auditor._is_python_file(str(py_file)) is True
            assert auditor._is_python_file(str(txt_file)) is False
            assert auditor._is_python_file("nonexistent.py") is False
    
    def test_parse_create_table(self):
        """Test parsing CREATE TABLE statements."""
        auditor = CodeAuditor()
        
        sql = """
        CREATE TABLE data_test (
            id INT PRIMARY KEY,
            name VARCHAR(100),
            value FLOAT
        )
        """
        
        operations = auditor._parse_sql_statement(sql, "test.py", 1)
        
        assert len(operations) == 1
        assert operations[0].operation_type == OperationType.CREATE
        assert operations[0].table_name == "data_test"
        assert "id" in operations[0].columns
        assert "name" in operations[0].columns
        assert "value" in operations[0].columns
    
    def test_parse_insert_statement(self):
        """Test parsing INSERT statements."""
        auditor = CodeAuditor()
        
        sql = "INSERT INTO users (id, name, email) VALUES (1, 'John', 'john@example.com')"
        
        operations = auditor._parse_sql_statement(sql, "test.py", 1)
        
        assert len(operations) == 1
        assert operations[0].operation_type == OperationType.INSERT
        assert operations[0].table_name == "users"
        assert operations[0].columns == ["id", "name", "email"]
    
    def test_parse_update_statement(self):
        """Test parsing UPDATE statements."""
        auditor = CodeAuditor()
        
        sql = "UPDATE users SET name='Jane', email='jane@example.com' WHERE id=1"
        
        operations = auditor._parse_sql_statement(sql, "test.py", 1)
        
        assert len(operations) == 1
        assert operations[0].operation_type == OperationType.UPDATE
        assert operations[0].table_name == "users"
        assert "name" in operations[0].columns
        assert "email" in operations[0].columns
    
    def test_parse_delete_statement(self):
        """Test parsing DELETE statements."""
        auditor = CodeAuditor()
        
        sql = "DELETE FROM users WHERE id=1"
        
        operations = auditor._parse_sql_statement(sql, "test.py", 1)
        
        assert len(operations) == 1
        assert operations[0].operation_type == OperationType.DELETE
        assert operations[0].table_name == "users"
    
    def test_parse_select_statement(self):
        """Test parsing SELECT statements."""
        auditor = CodeAuditor()
        
        sql = "SELECT id, name, email FROM users WHERE active=1"
        
        operations = auditor._parse_sql_statement(sql, "test.py", 1)
        
        assert len(operations) == 1
        assert operations[0].operation_type == OperationType.SELECT
        assert operations[0].table_name == "users"
        assert "id" in operations[0].columns
        assert "name" in operations[0].columns
        assert "email" in operations[0].columns
    
    def test_extract_table_operations_from_file(self):
        """Test extracting operations from a Python file."""
        auditor = CodeAuditor()
        
        # Create a temporary Python file with SQL
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_db.py"
            test_file.write_text('''
def create_table():
    sql = """
    CREATE TABLE test_table (
        id INT PRIMARY KEY,
        name VARCHAR(100)
    )
    """
    execute_query(sql)

def insert_data():
    sql = "INSERT INTO test_table (id, name) VALUES (1, 'Test')"
    execute_query(sql)
''')
            
            operations = auditor.extract_table_operations(str(test_file))
            
            # Should find both CREATE and INSERT operations
            assert len(operations) >= 2
            
            create_ops = [op for op in operations if op.operation_type == OperationType.CREATE]
            insert_ops = [op for op in operations if op.operation_type == OperationType.INSERT]
            
            assert len(create_ops) >= 1
            assert len(insert_ops) >= 1
            
            assert create_ops[0].table_name == "test_table"
            assert insert_ops[0].table_name == "test_table"
    
    def test_build_operation_map(self):
        """Test building operation map."""
        auditor = CodeAuditor()
        
        # Create a temporary Python file
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_db.py"
            test_file.write_text('''
sql1 = "CREATE TABLE users (id INT, name VARCHAR(100))"
sql2 = "INSERT INTO users (id, name) VALUES (1, 'John')"
sql3 = "INSERT INTO posts (id, title) VALUES (1, 'Hello')"
''')
            
            auditor.extract_table_operations(str(test_file))
            operation_map = auditor.build_operation_map()
            
            # Should have operations for both tables
            assert "users" in operation_map
            assert "posts" in operation_map
            
            # Users should have CREATE and INSERT
            assert len(operation_map["users"]) >= 2
            
            # Posts should have INSERT
            assert len(operation_map["posts"]) >= 1
    
    def test_scan_directory(self):
        """Test scanning a directory for Python files."""
        auditor = CodeAuditor()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directory structure
            tmpdir_path = Path(tmpdir)
            
            # Create Python file with SQL
            (tmpdir_path / "db_ops.py").write_text('''
sql = "CREATE TABLE test (id INT)"
''')
            
            # Create subdirectory with Python file
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()
            (subdir / "more_ops.py").write_text('''
sql = "INSERT INTO test (id) VALUES (1)"
''')
            
            # Create non-Python file (should be ignored)
            (tmpdir_path / "readme.txt").write_text("Not Python")
            
            # Scan directory
            locations = auditor.scan_directory(str(tmpdir_path))
            
            # Should find operations in both Python files
            assert len(locations) >= 2
            assert len(auditor.scanned_files) == 2
    
    def test_get_operations_by_table(self):
        """Test filtering operations by table name."""
        auditor = CodeAuditor()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
sql1 = "CREATE TABLE users (id INT)"
sql2 = "INSERT INTO users (id) VALUES (1)"
sql3 = "INSERT INTO posts (id) VALUES (1)"
''')
            
            auditor.extract_table_operations(str(test_file))
            
            users_ops = auditor.get_operations_by_table("users")
            posts_ops = auditor.get_operations_by_table("posts")
            
            assert len(users_ops) >= 2
            assert len(posts_ops) >= 1
    
    def test_get_operations_by_type(self):
        """Test filtering operations by type."""
        auditor = CodeAuditor()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
sql1 = "CREATE TABLE users (id INT)"
sql2 = "INSERT INTO users (id) VALUES (1)"
sql3 = "UPDATE users SET id=2 WHERE id=1"
''')
            
            auditor.extract_table_operations(str(test_file))
            
            create_ops = auditor.get_operations_by_type(OperationType.CREATE)
            insert_ops = auditor.get_operations_by_type(OperationType.INSERT)
            update_ops = auditor.get_operations_by_type(OperationType.UPDATE)
            
            assert len(create_ops) >= 1
            assert len(insert_ops) >= 1
            assert len(update_ops) >= 1
    
    def test_get_tables(self):
        """Test getting all table names."""
        auditor = CodeAuditor()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
sql1 = "CREATE TABLE users (id INT)"
sql2 = "INSERT INTO posts (id) VALUES (1)"
sql3 = "UPDATE comments SET text='hi' WHERE id=1"
''')
            
            auditor.extract_table_operations(str(test_file))
            tables = auditor.get_tables()
            
            assert "users" in tables
            assert "posts" in tables
            assert "comments" in tables
            assert len(tables) == 3
    
    def test_parse_save_structured_data_calls(self):
        """Test parsing save_structured_data function calls."""
        auditor = CodeAuditor()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_scraper.py"
            test_file.write_text('''
import asyncio
from database_handler import DatabaseHandler

async def scrape_data():
    db_handler = DatabaseHandler()
    
    # Direct string literal
    await db_handler.save_structured_data('data_biodiesel_hip', data_list)
    
    # Another call
    await db_handler.save_structured_data('data_bioetanol_hip', more_data)
    
    # Variable table name (should still be detected)
    table_name = 'data_fossil'
    await db_handler.save_structured_data(table_name, fossil_data)
''')
            
            operations = auditor.parse_save_structured_data_calls(str(test_file))
            
            # Should find all three save_structured_data calls
            assert len(operations) == 3
            
            # Check table names
            table_names = [op.table_name for op in operations]
            assert 'data_biodiesel_hip' in table_names
            assert 'data_bioetanol_hip' in table_names
            # Variable names are captured with <variable:> prefix
            assert any('table_name' in name for name in table_names)
            
            # All should be INSERT operations
            for op in operations:
                assert op.operation_type == OperationType.INSERT
    
    def test_detect_save_structured_data_in_extract(self):
        """Test that extract_table_operations includes save_structured_data calls."""
        auditor = CodeAuditor()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_mixed.py"
            test_file.write_text('''
# Mix of SQL and save_structured_data calls
sql = "CREATE TABLE test_table (id INT, name VARCHAR(100))"

async def save_data():
    await db_handler.save_structured_data('test_table', data)
    
sql2 = "INSERT INTO another_table (id) VALUES (1)"
''')
            
            operations = auditor.extract_table_operations(str(test_file))
            
            # Should find CREATE, INSERT (SQL), and INSERT (save_structured_data)
            assert len(operations) >= 3
            
            # Check we have operations for both tables
            table_names = {op.table_name for op in operations}
            assert 'test_table' in table_names
            assert 'another_table' in table_names
    
    def test_get_function_name(self):
        """Test extracting function names from AST nodes."""
        auditor = CodeAuditor()
        
        # Test with simple function call
        code = "save_structured_data('table', data)"
        tree = ast.parse(code)
        call_node = tree.body[0].value
        
        func_name = auditor._get_function_name(call_node.func)
        assert func_name == 'save_structured_data'
        
        # Test with method call
        code2 = "db_handler.save_structured_data('table', data)"
        tree2 = ast.parse(code2)
        call_node2 = tree2.body[0].value
        
        func_name2 = auditor._get_function_name(call_node2.func)
        assert func_name2 == 'save_structured_data'
    
    def test_extract_table_name_from_call(self):
        """Test extracting table name from function call arguments."""
        auditor = CodeAuditor()
        
        # Test with string literal
        code = "save_structured_data('my_table', data)"
        tree = ast.parse(code)
        call_node = tree.body[0].value
        
        table_name = auditor._extract_table_name_from_call(call_node)
        assert table_name == 'my_table'
        
        # Test with variable
        code2 = "save_structured_data(table_var, data)"
        tree2 = ast.parse(code2)
        call_node2 = tree2.body[0].value
        
        table_name2 = auditor._extract_table_name_from_call(call_node2)
        assert table_name2 == '<variable:table_var>'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
