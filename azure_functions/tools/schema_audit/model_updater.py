"""
Model Updater for Database Schema Audit System.

This module updates models.py and database_schema.sql files to match the reference schema
from BACPAC while preserving existing business logic and validation code.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import logging

from .models import (
    DatabaseSchema,
    TableSchema,
    ColumnSchema
)

logger = logging.getLogger(__name__)


class ModelUpdater:
    """
    Updates models.py and database_schema.sql to match reference schema.
    
    This class generates Python dataclasses for structured data tables and
    updates SQL schema files while preserving existing business logic.
    """
    
    # Standard news tables to exclude from model generation
    EXCLUDED_TABLES = {
        'news_articles', 'news_sources', 'keywords',
        'article_keywords', 'scraping_logs', 'sentiment_analyses',
        'sentiment_analysis_articles', 'execution_logs', 'configuration'
    }
    
    # SQL type to Python type mapping
    SQL_TO_PYTHON_TYPE = {
        'int': 'int',
        'bigint': 'int',
        'smallint': 'int',
        'tinyint': 'int',
        'bit': 'bool',
        'decimal': 'float',
        'numeric': 'float',
        'money': 'float',
        'smallmoney': 'float',
        'float': 'float',
        'real': 'float',
        'datetime': 'datetime',
        'datetime2': 'datetime',
        'smalldatetime': 'datetime',
        'date': 'datetime',
        'time': 'datetime',
        'datetimeoffset': 'datetime',
        'char': 'str',
        'varchar': 'str',
        'text': 'str',
        'nchar': 'str',
        'nvarchar': 'str',
        'ntext': 'str',
        'binary': 'bytes',
        'varbinary': 'bytes',
        'image': 'bytes',
        'uniqueidentifier': 'str',
        'xml': 'str',
        'json': 'str'
    }
    
    def __init__(self):
        """Initialize the model updater."""
        self.reference_schema: Optional[DatabaseSchema] = None
        self.existing_business_logic: Dict[str, List[str]] = {}
    
    def update_models_file(
        self,
        reference_schema: DatabaseSchema,
        models_file_path: str,
        dry_run: bool = False
    ) -> bool:
        """
        Update models.py file with dataclasses for structured data tables.
        
        Args:
            reference_schema: Reference schema from BACPAC
            models_file_path: Path to models.py file
            dry_run: If True, don't write changes to disk
            
        Returns:
            True if update successful, False otherwise
        """
        logger.info(f"Updating models file: {models_file_path}")
        self.reference_schema = reference_schema
        
        models_path = Path(models_file_path)
        if not models_path.exists():
            logger.error(f"Models file not found: {models_file_path}")
            return False
        
        try:
            # Read existing models file
            with open(models_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            
            # Preserve existing business logic
            self._preserve_business_logic(existing_content)
            
            # Get structured data tables (exclude standard news tables)
            structured_tables = self._get_structured_data_tables(reference_schema)
            
            if not structured_tables:
                logger.info("No structured data tables found to generate models for")
                return True
            
            # Generate new dataclasses
            new_dataclasses = []
            for table_name, table_schema in structured_tables.items():
                dataclass_code = self._generate_dataclass(table_name, table_schema)
                new_dataclasses.append(dataclass_code)
            
            # Build updated content
            updated_content = self._build_updated_models_content(
                existing_content,
                new_dataclasses
            )
            
            if dry_run:
                logger.info("Dry run mode: Not writing changes to disk")
                logger.info(f"Would generate {len(new_dataclasses)} dataclasses")
                return True
            
            # Write updated content
            with open(models_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.info(f"Successfully updated models file with {len(new_dataclasses)} dataclasses")
            return True
            
        except Exception as e:
            logger.error(f"Error updating models file: {e}")
            return False
    
    def _get_structured_data_tables(self, schema: DatabaseSchema) -> Dict[str, TableSchema]:
        """
        Get structured data tables (exclude standard news tables).
        
        Args:
            schema: Database schema
            
        Returns:
            Dictionary of table name to TableSchema for structured data tables
        """
        structured_tables = {}
        for table_name, table_schema in schema.tables.items():
            if table_name.lower() not in self.EXCLUDED_TABLES:
                structured_tables[table_name] = table_schema
        
        logger.info(f"Found {len(structured_tables)} structured data tables")
        return structured_tables
    
    def _generate_dataclass(self, table_name: str, table_schema: TableSchema) -> str:
        """
        Generate Python dataclass code for a table.
        
        Args:
            table_name: Name of the table
            table_schema: Schema of the table
            
        Returns:
            Python code string for the dataclass
        """
        # Convert table name to class name (e.g., data_biodiesel_hip -> DataBiodieselHip)
        class_name = self._table_name_to_class_name(table_name)
        
        # Generate field definitions
        fields = []
        for column in table_schema.columns:
            field_def = self._generate_field_definition(column)
            fields.append(field_def)
        
        # Build dataclass code
        lines = [
            f"@dataclass",
            f"class {class_name}:",
            f'    """',
            f'    Data model for {table_name} table.',
            f'    Auto-generated from database schema.',
            f'    """'
        ]
        
        # Add fields
        for field in fields:
            lines.append(f"    {field}")
        
        # Add empty line if no fields (shouldn't happen but for safety)
        if not fields:
            lines.append("    pass")
        
        return '\n'.join(lines)
    
    def _table_name_to_class_name(self, table_name: str) -> str:
        """
        Convert table name to Python class name.
        
        Examples:
            data_biodiesel_hip -> DataBiodieselHip
            data_harga_ebt -> DataHargaEbt
            
        Args:
            table_name: Database table name
            
        Returns:
            Python class name
        """
        # Split by underscore and capitalize each part
        parts = table_name.split('_')
        class_name = ''.join(word.capitalize() for word in parts)
        return class_name
    
    def _generate_field_definition(self, column: ColumnSchema) -> str:
        """
        Generate Python field definition for a column.
        
        Args:
            column: Column schema
            
        Returns:
            Python field definition string
        """
        # Get Python type
        python_type = self._sql_type_to_python_type(column.data_type)
        
        # Make optional if nullable
        if column.nullable:
            type_annotation = f"Optional[{python_type}]"
            default_value = " = None"
        else:
            type_annotation = python_type
            default_value = ""
        
        # Handle identity columns (auto-increment)
        if column.is_identity:
            type_annotation = f"Optional[{python_type}]"
            default_value = " = None"
        
        # Handle default values
        if column.default_value and not column.is_identity:
            if python_type == 'str':
                default_value = f' = "{column.default_value}"'
            elif python_type == 'bool':
                default_value = f' = {column.default_value}'
            elif python_type in ['int', 'float']:
                default_value = f' = {column.default_value}'
            elif python_type == 'datetime':
                if 'getutcdate' in column.default_value.lower() or 'getdate' in column.default_value.lower():
                    default_value = " = field(default_factory=datetime.utcnow)"
                else:
                    default_value = " = None"
        
        return f"{column.name}: {type_annotation}{default_value}"
    
    def _sql_type_to_python_type(self, sql_type: str) -> str:
        """
        Convert SQL data type to Python type.
        
        Args:
            sql_type: SQL data type (e.g., 'nvarchar', 'int', 'datetime2')
            
        Returns:
            Python type string
        """
        # Normalize SQL type (remove size specifications)
        base_type = sql_type.lower().split('(')[0].strip()
        
        # Look up in mapping
        python_type = self.SQL_TO_PYTHON_TYPE.get(base_type, 'str')
        return python_type
    
    def _preserve_business_logic(self, existing_content: str) -> None:
        """
        Extract and preserve business logic from existing models.
        
        This method identifies custom validation methods, business logic,
        and other code that should be preserved when regenerating models.
        
        Args:
            existing_content: Content of existing models.py file
        """
        logger.info("Preserving existing business logic")
        
        try:
            # Parse existing Python code
            tree = ast.parse(existing_content)
            
            # Find all class definitions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    
                    # Extract methods that look like business logic
                    business_methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            # Preserve custom methods (not __init__, __post_init__, etc.)
                            if not item.name.startswith('_') or item.name in ['__post_init__', '__str__', '__eq__']:
                                # Get the source code for this method
                                method_lines = ast.get_source_segment(existing_content, item)
                                if method_lines:
                                    business_methods.append(method_lines)
                    
                    if business_methods:
                        self.existing_business_logic[class_name] = business_methods
                        logger.info(f"Preserved {len(business_methods)} methods from {class_name}")
        
        except SyntaxError as e:
            logger.warning(f"Could not parse existing models file: {e}")
        except Exception as e:
            logger.warning(f"Error preserving business logic: {e}")
    
    def _build_updated_models_content(
        self,
        existing_content: str,
        new_dataclasses: List[str]
    ) -> str:
        """
        Build updated models.py content by merging existing and new code.
        
        Args:
            existing_content: Existing models.py content
            new_dataclasses: List of new dataclass code strings
            
        Returns:
            Updated models.py content
        """
        # Find the end of existing imports and the start of class definitions
        lines = existing_content.split('\n')
        
        # Find where to insert new dataclasses (after existing classes or at end)
        # For now, append new dataclasses at the end
        updated_lines = lines.copy()
        
        # Add separator comment
        updated_lines.append('\n')
        updated_lines.append('# =====================================================')
        updated_lines.append('# Structured Data Models (Auto-generated)')
        updated_lines.append('# =====================================================')
        updated_lines.append('')
        
        # Add new dataclasses
        for dataclass_code in new_dataclasses:
            updated_lines.append(dataclass_code)
            updated_lines.append('')  # Empty line between classes
        
        return '\n'.join(updated_lines)
    
    def update_database_schema_sql(
        self,
        reference_schema: DatabaseSchema,
        sql_file_path: str,
        dry_run: bool = False
    ) -> bool:
        """
        Update database_schema.sql file to match reference schema.
        
        Args:
            reference_schema: Reference schema from BACPAC
            sql_file_path: Path to database_schema.sql file
            dry_run: If True, don't write changes to disk
            
        Returns:
            True if update successful, False otherwise
        """
        logger.info(f"Updating SQL schema file: {sql_file_path}")
        self.reference_schema = reference_schema
        
        sql_path = Path(sql_file_path)
        if not sql_path.exists():
            logger.error(f"SQL schema file not found: {sql_file_path}")
            return False
        
        try:
            # Read existing SQL file
            with open(sql_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            
            # Get structured data tables
            structured_tables = self._get_structured_data_tables(reference_schema)
            
            if not structured_tables:
                logger.info("No structured data tables found to generate SQL for")
                return True
            
            # Generate CREATE TABLE statements
            create_statements = []
            for table_name, table_schema in structured_tables.items():
                create_sql = self._generate_create_table_sql(table_name, table_schema)
                create_statements.append(create_sql)
            
            # Build updated SQL content
            updated_content = self._build_updated_sql_content(
                existing_content,
                create_statements
            )
            
            if dry_run:
                logger.info("Dry run mode: Not writing changes to disk")
                logger.info(f"Would generate {len(create_statements)} CREATE TABLE statements")
                return True
            
            # Write updated content
            with open(sql_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.info(f"Successfully updated SQL schema file with {len(create_statements)} tables")
            return True
            
        except Exception as e:
            logger.error(f"Error updating SQL schema file: {e}")
            return False
    
    def _generate_create_table_sql(self, table_name: str, table_schema: TableSchema) -> str:
        """
        Generate CREATE TABLE SQL statement for a table.
        
        Args:
            table_name: Name of the table
            table_schema: Schema of the table
            
        Returns:
            SQL CREATE TABLE statement
        """
        lines = [f"-- {table_name} table"]
        lines.append(f"CREATE TABLE {table_name} (")
        
        # Generate column definitions
        column_defs = []
        for column in table_schema.columns:
            col_def = self._generate_column_sql(column)
            column_defs.append(f"    {col_def}")
        
        # Add primary key constraint if exists
        if table_schema.primary_key:
            pk_columns = ', '.join(table_schema.primary_key)
            column_defs.append(f"    CONSTRAINT PK_{table_name} PRIMARY KEY ({pk_columns})")
        
        # Add foreign key constraints
        for fk in table_schema.foreign_keys:
            fk_def = self._generate_foreign_key_sql(fk)
            column_defs.append(f"    {fk_def}")
        
        # Join column definitions
        lines.append(',\n'.join(column_defs))
        lines.append(");")
        
        # Add indexes
        for index in table_schema.indexes:
            index_sql = self._generate_index_sql(table_name, index)
            lines.append(index_sql)
        
        return '\n'.join(lines)
    
    def _generate_column_sql(self, column: ColumnSchema) -> str:
        """
        Generate SQL column definition.
        
        Args:
            column: Column schema
            
        Returns:
            SQL column definition string
        """
        parts = [column.name, column.data_type.upper()]
        
        # Add size/precision if applicable
        if column.max_length and column.max_length > 0:
            if column.max_length == -1:  # MAX
                parts[1] = f"{parts[1]}(MAX)"
            else:
                parts[1] = f"{parts[1]}({column.max_length})"
        elif column.precision and column.precision > 0:
            if column.scale and column.scale > 0:
                parts[1] = f"{parts[1]}({column.precision},{column.scale})"
            else:
                parts[1] = f"{parts[1]}({column.precision})"
        
        # Add IDENTITY if applicable
        if column.is_identity:
            parts.append("IDENTITY(1,1)")
        
        # Add NULL/NOT NULL
        if column.nullable:
            parts.append("NULL")
        else:
            parts.append("NOT NULL")
        
        # Add DEFAULT if applicable
        if column.default_value and not column.is_identity:
            parts.append(f"DEFAULT {column.default_value}")
        
        return ' '.join(parts)
    
    def _generate_foreign_key_sql(self, fk: 'ForeignKeySchema') -> str:
        """
        Generate SQL foreign key constraint.
        
        Args:
            fk: Foreign key schema
            
        Returns:
            SQL foreign key constraint string
        """
        fk_sql = f"CONSTRAINT {fk.name} FOREIGN KEY ({fk.column}) REFERENCES {fk.referenced_table}({fk.referenced_column})"
        
        if fk.on_delete:
            fk_sql += f" ON DELETE {fk.on_delete}"
        if fk.on_update:
            fk_sql += f" ON UPDATE {fk.on_update}"
        
        return fk_sql
    
    def _generate_index_sql(self, table_name: str, index: 'IndexSchema') -> str:
        """
        Generate SQL CREATE INDEX statement.
        
        Args:
            table_name: Name of the table
            index: Index schema
            
        Returns:
            SQL CREATE INDEX statement
        """
        index_type = "UNIQUE " if index.is_unique else ""
        clustered = "CLUSTERED " if index.is_clustered else ""
        columns = ', '.join(index.columns)
        
        index_sql = f"CREATE {index_type}{clustered}INDEX {index.name} ON {table_name}({columns})"
        
        if index.filter_condition:
            index_sql += f" WHERE {index.filter_condition}"
        
        index_sql += ";"
        return index_sql
    
    def _build_updated_sql_content(
        self,
        existing_content: str,
        create_statements: List[str]
    ) -> str:
        """
        Build updated database_schema.sql content.
        
        Args:
            existing_content: Existing SQL file content
            create_statements: List of CREATE TABLE statements
            
        Returns:
            Updated SQL content
        """
        # Append new tables at the end with a separator comment
        lines = [existing_content.rstrip()]
        lines.append('\n')
        lines.append('-- =====================================================')
        lines.append('-- Structured Data Tables (Auto-generated)')
        lines.append('-- =====================================================')
        lines.append('')
        
        for statement in create_statements:
            lines.append(statement)
            lines.append('')
        
        return '\n'.join(lines)
    
    def update_database_handler(
        self,
        reference_schema: DatabaseSchema,
        handler_file_path: str,
        dry_run: bool = False
    ) -> bool:
        """
        Update database_handler.py with save methods for all structured data tables.
        
        Args:
            reference_schema: Reference schema from BACPAC
            handler_file_path: Path to database_handler.py file
            dry_run: If True, don't write changes to disk
            
        Returns:
            True if update successful, False otherwise
        """
        logger.info(f"Updating database handler file: {handler_file_path}")
        self.reference_schema = reference_schema
        
        handler_path = Path(handler_file_path)
        if not handler_path.exists():
            logger.error(f"Database handler file not found: {handler_file_path}")
            return False
        
        try:
            # Read existing handler file
            with open(handler_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            
            # Get structured data tables
            structured_tables = self._get_structured_data_tables(reference_schema)
            
            if not structured_tables:
                logger.info("No structured data tables found to generate save methods for")
                return True
            
            # Check completeness - which tables need save methods
            missing_methods = self._check_completeness(existing_content, structured_tables)
            
            if not missing_methods:
                logger.info("All structured data tables already have save methods")
                return True
            
            logger.info(f"Found {len(missing_methods)} tables missing save methods")
            
            # Generate save methods for missing tables
            new_methods = []
            for table_name, table_schema in missing_methods.items():
                method_code = self._generate_save_method(table_name, table_schema)
                new_methods.append(method_code)
            
            # Build updated content
            updated_content = self._build_updated_handler_content(
                existing_content,
                new_methods
            )
            
            if dry_run:
                logger.info("Dry run mode: Not writing changes to disk")
                logger.info(f"Would generate {len(new_methods)} save methods")
                return True
            
            # Write updated content
            with open(handler_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            logger.info(f"Successfully updated database handler with {len(new_methods)} save methods")
            return True
            
        except Exception as e:
            logger.error(f"Error updating database handler: {e}")
            return False
    
    def _generate_save_method(self, table_name: str, table_schema: TableSchema) -> str:
        """
        Generate save method for a structured data table.
        
        Args:
            table_name: Name of the table
            table_schema: Schema of the table
            
        Returns:
            Python code string for the save method
        """
        # Convert table name to method name (e.g., data_biodiesel_hip -> save_biodiesel_hip_data)
        method_name = self._table_name_to_method_name(table_name)
        
        # Get class name for type hint
        class_name = self._table_name_to_class_name(table_name)
        
        # Get column names (excluding identity columns)
        columns = [col.name for col in table_schema.columns if not col.is_identity]
        column_names = ', '.join(columns)
        placeholders = ', '.join(['?' for _ in columns])
        
        # Build method code
        lines = [
            f"    async def {method_name}(self, data: List[{class_name}]) -> int:",
            f'        """',
            f'        Save {table_name} data to the database.',
            f'        ',
            f'        Args:',
            f'            data: List of {class_name} objects to save',
            f'            ',
            f'        Returns:',
            f'            Number of rows saved',
            f'        """',
            f'        if not data:',
            f'            return 0',
            f'        ',
            f'        async def _save_operation():',
            f'            async with self._get_connection() as conn:',
            f'                cursor = conn.cursor()',
            f'                try:',
            f'                    insert_query = """',
            f'                    INSERT INTO {table_name} ({column_names})',
            f'                    VALUES ({placeholders})',
            f'                    """',
            f'                    ',
            f'                    rows = [',
            f'                        tuple(',
        ]
        
        # Add field access for each column
        field_accesses = [f'                            item.{col.name}' for col in table_schema.columns if not col.is_identity]
        lines.append(',\n'.join(field_accesses))
        
        lines.extend([
            f'                        )',
            f'                        for item in data',
            f'                    ]',
            f'                    ',
            f'                    self.logger.info(f"💾 {method_name}: Saving {{len(data)}} rows to {table_name}")',
            f'                    cursor.executemany(insert_query, rows)',
            f'                    ',
            f'                    conn.commit()',
            f'                    self.logger.info(f"🚀 {method_name}: Successfully saved {{len(data)}} rows to {table_name}")',
            f'                    return len(data)',
            f'                except Exception as e:',
            f'                    conn.rollback()',
            f'                    self.logger.error(f"❌ {method_name}: Failed to save to {table_name}: {{e}}")',
            f'                    raise DatabaseError(f"Failed to save {table_name} data: {{str(e)}}")',
            f'        ',
            f'        return await self._execute_with_retry(_save_operation)'
        ])
        
        return '\n'.join(lines)
    
    def _table_name_to_method_name(self, table_name: str) -> str:
        """
        Convert table name to method name.
        
        Examples:
            data_biodiesel_hip -> save_biodiesel_hip_data
            data_harga_ebt -> save_harga_ebt_data
            
        Args:
            table_name: Database table name
            
        Returns:
            Python method name
        """
        # Remove 'data_' prefix if present
        if table_name.startswith('data_'):
            base_name = table_name[5:]  # Remove 'data_' prefix
            return f"save_{base_name}_data"
        else:
            return f"save_{table_name}_data"
    
    def _check_completeness(
        self,
        handler_content: str,
        structured_tables: Dict[str, TableSchema]
    ) -> Dict[str, TableSchema]:
        """
        Check which structured data tables are missing save methods.
        
        Args:
            handler_content: Content of database_handler.py file
            structured_tables: Dictionary of structured data tables
            
        Returns:
            Dictionary of tables that need save methods (table_name -> TableSchema)
        """
        missing_methods = {}
        
        for table_name, table_schema in structured_tables.items():
            # Generate expected method name
            method_name = self._table_name_to_method_name(table_name)
            
            # Check if method exists in handler content
            # Look for method definition pattern: "async def method_name("
            method_pattern = f"async def {method_name}("
            
            if method_pattern not in handler_content:
                logger.info(f"Missing save method for table: {table_name} (expected: {method_name})")
                missing_methods[table_name] = table_schema
            else:
                logger.debug(f"Save method already exists for table: {table_name}")
        
        return missing_methods
    
    def _build_updated_handler_content(
        self,
        existing_content: str,
        new_methods: List[str]
    ) -> str:
        """
        Build updated database_handler.py content by adding new save methods.
        
        Args:
            existing_content: Existing database_handler.py content
            new_methods: List of new method code strings
            
        Returns:
            Updated database_handler.py content
        """
        # Find the DatabaseHandler class and insert methods before the closing
        # We'll insert before the close() method or at the end of the class
        
        lines = existing_content.split('\n')
        
        # Find the best insertion point - before close() method or before factory function
        insertion_index = None
        
        # Look for the close() method or factory function
        for i, line in enumerate(lines):
            if 'async def close(self)' in line or 'def create_database_handler' in line:
                # Insert before this method, accounting for proper indentation
                insertion_index = i
                break
        
        if insertion_index is None:
            # If we can't find a good spot, append at the end of the class
            # Find the last method in DatabaseHandler class
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip().startswith('async def ') or lines[i].strip().startswith('def '):
                    # Find the end of this method
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip() and not lines[j].startswith(' '):
                            insertion_index = j
                            break
                    break
        
        if insertion_index is None:
            # Fallback: append at the end
            insertion_index = len(lines)
        
        # Build updated content
        updated_lines = lines[:insertion_index]
        
        # Add separator comment
        updated_lines.append('')
        updated_lines.append('    # =====================================================')
        updated_lines.append('    # Structured Data Save Methods (Auto-generated)')
        updated_lines.append('    # =====================================================')
        updated_lines.append('')
        
        # Add new methods
        for method_code in new_methods:
            updated_lines.append(method_code)
            updated_lines.append('')
        
        # Add remaining content
        updated_lines.extend(lines[insertion_index:])
        
        return '\n'.join(updated_lines)
