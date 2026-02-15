"""
Schema Extractor for Database Schema Audit System.

This module extracts database schema from BACPAC files (SQL Server backup format).
BACPAC files are ZIP archives containing a model.xml file with the schema definition.
"""

import zipfile
import xml.etree.ElementTree as ET
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import logging

from .models import (
    DatabaseSchema,
    TableSchema,
    ColumnSchema,
    ForeignKeySchema,
    IndexSchema,
    ConstraintSchema
)

logger = logging.getLogger(__name__)


class SchemaExtractor:
    """
    Extracts database schema from BACPAC files.
    
    BACPAC is a SQL Server format that packages database schema and data
    into a ZIP file containing XML model definitions.
    """
    
    # XML namespaces used in DacPac/BACPAC files
    NAMESPACES = {
        'dac': 'http://schemas.microsoft.com/sqlserver/dac/Serialization/2012/02',
        'data': 'http://schemas.microsoft.com/sqlserver/dac/Serialization/2012/02'
    }
    
    def __init__(self):
        """Initialize the schema extractor."""
        self.current_schema: Optional[DatabaseSchema] = None
    
    def extract_from_bacpac(self, bacpac_path: str) -> DatabaseSchema:
        """
        Extract schema from a BACPAC file.
        
        Args:
            bacpac_path: Path to the .bacpac file
            
        Returns:
            DatabaseSchema object containing the extracted schema
            
        Raises:
            FileNotFoundError: If BACPAC file doesn't exist
            ValueError: If BACPAC file is invalid or model.xml not found
        """
        logger.info(f"Extracting schema from BACPAC: {bacpac_path}")
        
        bacpac_file = Path(bacpac_path)
        if not bacpac_file.exists():
            raise FileNotFoundError(f"BACPAC file not found: {bacpac_path}")
        
        if not bacpac_file.suffix.lower() == '.bacpac':
            raise ValueError(f"File must have .bacpac extension: {bacpac_path}")
        
        try:
            with zipfile.ZipFile(bacpac_path, 'r') as zip_file:
                # BACPAC files contain a model.xml file with schema definition
                if 'model.xml' not in zip_file.namelist():
                    raise ValueError("Invalid BACPAC file: model.xml not found")
                
                # Read and parse the model.xml
                with zip_file.open('model.xml') as model_file:
                    xml_content = model_file.read().decode('utf-8')
                    schema = self.parse_dacpac_xml(xml_content)
                    
                # Set metadata
                schema.source_file = str(bacpac_file.absolute())
                schema.extracted_at = datetime.now()
                
                logger.info(f"Successfully extracted {len(schema.tables)} tables from BACPAC")
                return schema
                
        except zipfile.BadZipFile:
            raise ValueError(f"Invalid ZIP file: {bacpac_path}")
        except Exception as e:
            logger.error(f"Error extracting schema from BACPAC: {e}")
            raise

    
    def parse_dacpac_xml(self, xml_content: str) -> DatabaseSchema:
        """
        Parse DacPac XML model to extract schema.
        
        Args:
            xml_content: XML content from model.xml
            
        Returns:
            DatabaseSchema object
            
        Raises:
            ValueError: If XML is malformed or invalid
        """
        logger.info("Parsing DacPac XML model")
        
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML content: {e}")
        
        schema = DatabaseSchema()
        
        # Find all table elements in the XML
        # DacPac XML structure: Model/Element[@Type='SqlTable']
        # Note: Use .//* to search all descendants regardless of namespace
        for element in root.findall(".//*[@Type='SqlTable']"):
            table = self._parse_table_definition(element)
            if table:
                schema.tables[table.name] = table
                logger.debug(f"Parsed table: {table.name} with {len(table.columns)} columns")
        
        logger.info(f"Parsed {len(schema.tables)} tables from XML")
        return schema
    
    def _parse_table_definition(self, table_element: ET.Element) -> Optional[TableSchema]:
        """
        Parse a table definition from XML element.
        
        Args:
            table_element: XML Element representing a SqlTable
            
        Returns:
            TableSchema object or None if parsing fails
        """
        # Get table name from Name attribute
        table_name = table_element.get('Name')
        if not table_name:
            logger.warning("Table element missing Name attribute")
            return None
        
        # Extract just the table name (remove schema prefix if present)
        # Format is usually [dbo].[TableName] or dbo.TableName
        if '.' in table_name:
            table_name = table_name.split('.')[-1]
        table_name = table_name.strip('[]')
        
        logger.debug(f"Parsing table: {table_name}")
        
        table = TableSchema(name=table_name)
        
        # Parse columns - find all SqlSimpleColumn elements within this table
        for column_element in table_element.findall(".//*[@Type='SqlSimpleColumn']"):
            column = self._parse_column_definition(column_element)
            if column:
                table.columns.append(column)
        
        # Parse primary key
        pk_element = table_element.find(".//*[@Type='SqlPrimaryKeyConstraint']")
        if pk_element:
            pk_columns = []
            # Find column references in the primary key
            for col_ref in pk_element.findall(".//References"):
                col_name = col_ref.get('Name', '')
                if '.' in col_name:
                    col_name = col_name.split('.')[-1]
                col_name = col_name.strip('[]')
                if col_name:
                    pk_columns.append(col_name)
            if pk_columns:
                table.primary_key = pk_columns
        
        # Parse constraints (foreign keys, indexes, etc.)
        self._parse_constraints(table_element, table)
        
        return table
    
    def _parse_column_definition(self, column_element: ET.Element) -> Optional[ColumnSchema]:
        """
        Parse a column definition from XML element.
        
        Args:
            column_element: XML Element representing a SqlSimpleColumn
            
        Returns:
            ColumnSchema object or None if parsing fails
        """
        # Get column name
        column_name = column_element.get('Name')
        if not column_name:
            return None
        
        # Extract just the column name (remove table prefix if present)
        if '.' in column_name:
            column_name = column_name.split('.')[-1]
        column_name = column_name.strip('[]')
        
        column = ColumnSchema(name=column_name, data_type='')
        
        # Parse properties and relationships
        for child in column_element:
            # Handle Property elements
            if child.tag.endswith('}Property') or 'Property' in child.tag:
                prop_name = child.get('Name')
                prop_value = child.get('Value', '')
                
                if prop_name == 'IsNullable':
                    column.nullable = prop_value.lower() == 'true'
                elif prop_name == 'IsIdentity':
                    column.is_identity = prop_value.lower() == 'true'
                elif prop_name == 'DefaultValue':
                    column.default_value = prop_value
            
            # Handle Relationship elements
            elif child.tag.endswith('}Relationship') or 'Relationship' in child.tag:
                rel_name = child.get('Name')
                
                if rel_name == 'TypeSpecifier':
                    # Find SqlTypeSpecifier element
                    type_spec_elem = child.find(".//*[@Type='SqlTypeSpecifier']")
                    if type_spec_elem is not None:
                        # Get type name from References
                        datatype_ref = type_spec_elem.find(".//*")
                        for elem in type_spec_elem.iter():
                            if elem.tag.endswith('}References') or 'References' in elem.tag:
                                datatype_name = elem.get('Name', '')
                                # Extract type name (format: [TypeName])
                                datatype_name = datatype_name.strip('[]')
                                column.data_type = datatype_name
                                break
                        
                        # Parse length/precision/scale from SqlTypeSpecifier properties
                        for prop in type_spec_elem.iter():
                            if prop.tag.endswith('}Property') or 'Property' in prop.tag:
                                prop_name = prop.get('Name')
                                prop_value = prop.get('Value', '')
                                
                                if prop_name == 'Length':
                                    try:
                                        column.max_length = int(prop_value) if prop_value != 'Max' else -1
                                    except (ValueError, TypeError):
                                        pass
                                elif prop_name == 'Precision':
                                    try:
                                        column.precision = int(prop_value)
                                    except (ValueError, TypeError):
                                        pass
                                elif prop_name == 'Scale':
                                    try:
                                        column.scale = int(prop_value)
                                    except (ValueError, TypeError):
                                        pass
        
        return column
    
    def _parse_constraints(self, table_element: ET.Element, table: TableSchema) -> None:
        """
        Parse constraints (foreign keys, indexes) from table element.
        
        Args:
            table_element: XML Element representing a SqlTable
            table: TableSchema object to add constraints to
        """
        # Parse foreign keys - look in the entire model for FKs referencing this table
        # Foreign keys are defined separately in the model, not within the table element
        # We'll handle this in a second pass if needed
        
        # Parse indexes - look for SqlIndex elements that reference this table
        # Indexes are also defined separately
        
        # Parse check constraints
        for check_element in table_element.findall(".//*[@Type='SqlCheckConstraint']"):
            constraint = self._parse_check_constraint(check_element)
            if constraint:
                table.constraints.append(constraint)
    
    def _parse_foreign_key(self, fk_element: ET.Element) -> Optional[ForeignKeySchema]:
        """Parse a foreign key constraint from XML element."""
        fk_name = fk_element.get('Name', '')
        if '.' in fk_name:
            fk_name = fk_name.split('.')[-1]
        fk_name = fk_name.strip('[]')
        
        # Get column name
        column_ref = fk_element.find(".//References")
        if column_ref is None:
            return None
        
        column_name = column_ref.get('Name', '')
        if '.' in column_name:
            column_name = column_name.split('.')[-1]
        column_name = column_name.strip('[]')
        
        # Get referenced table and column
        foreign_table_ref = fk_element.find(".//References")
        if foreign_table_ref is None:
            return None
        
        foreign_table = foreign_table_ref.get('Name', '')
        if '.' in foreign_table:
            foreign_table = foreign_table.split('.')[-1]
        foreign_table = foreign_table.strip('[]')
        
        foreign_column_ref = fk_element.find(".//References")
        if foreign_column_ref is None:
            return None
        
        foreign_column = foreign_column_ref.get('Name', '')
        if '.' in foreign_column:
            foreign_column = foreign_column.split('.')[-1]
        foreign_column = foreign_column.strip('[]')
        
        # Get ON DELETE and ON UPDATE actions
        on_delete = None
        on_update = None
        for prop in fk_element.findall(".//Property"):
            prop_name = prop.get('Name')
            prop_value = prop.get('Value', '')
            if prop_name == 'DeleteAction':
                on_delete = prop_value
            elif prop_name == 'UpdateAction':
                on_update = prop_value
        
        return ForeignKeySchema(
            name=fk_name,
            column=column_name,
            referenced_table=foreign_table,
            referenced_column=foreign_column,
            on_delete=on_delete,
            on_update=on_update
        )
    
    def _parse_index(self, index_element: ET.Element) -> Optional[IndexSchema]:
        """Parse an index from XML element."""
        index_name = index_element.get('Name', '')
        if '.' in index_name:
            index_name = index_name.split('.')[-1]
        index_name = index_name.strip('[]')
        
        # Get index columns
        columns = []
        for col_ref in index_element.findall(".//References"):
            col_name = col_ref.get('Name', '')
            if '.' in col_name:
                col_name = col_name.split('.')[-1]
            col_name = col_name.strip('[]')
            if col_name:
                columns.append(col_name)
        
        if not columns:
            return None
        
        # Get index properties
        is_unique = False
        is_clustered = False
        filter_condition = None
        
        for prop in index_element.findall(".//Property"):
            prop_name = prop.get('Name')
            prop_value = prop.get('Value', '')
            if prop_name == 'IsUnique':
                is_unique = prop_value.lower() == 'true'
            elif prop_name == 'IsClustered':
                is_clustered = prop_value.lower() == 'true'
            elif prop_name == 'FilterPredicate':
                filter_condition = prop_value
        
        return IndexSchema(
            name=index_name,
            columns=columns,
            is_unique=is_unique,
            is_clustered=is_clustered,
            filter_condition=filter_condition
        )
    
    def _parse_check_constraint(self, check_element: ET.Element) -> Optional[ConstraintSchema]:
        """Parse a check constraint from XML element."""
        constraint_name = check_element.get('Name', '')
        if '.' in constraint_name:
            constraint_name = constraint_name.split('.')[-1]
        constraint_name = constraint_name.strip('[]')
        
        # Get constraint definition
        definition = ''
        for prop in check_element.findall(".//Property"):
            if prop.get('Name') == 'Expression':
                definition = prop.get('Value', '')
                break
        
        if not definition:
            return None
        
        return ConstraintSchema(
            name=constraint_name,
            constraint_type='CHECK',
            definition=definition
        )
    
    def export_to_json(self, schema: DatabaseSchema, output_path: str) -> None:
        """
        Export schema to JSON format for serialization.
        
        Args:
            schema: DatabaseSchema object to export
            output_path: Path where JSON file will be written
            
        Raises:
            IOError: If file cannot be written
        """
        logger.info(f"Exporting schema to JSON: {output_path}")
        
        # Convert schema to dictionary
        schema_dict = {
            'version': schema.version,
            'extracted_at': schema.extracted_at.isoformat() if schema.extracted_at else None,
            'source_file': schema.source_file,
            'tables': {}
        }
        
        for table_name, table in schema.tables.items():
            table_dict = {
                'name': table.name,
                'columns': [
                    {
                        'name': col.name,
                        'data_type': col.data_type,
                        'nullable': col.nullable,
                        'default_value': col.default_value,
                        'max_length': col.max_length,
                        'precision': col.precision,
                        'scale': col.scale,
                        'is_identity': col.is_identity
                    }
                    for col in table.columns
                ],
                'primary_key': table.primary_key,
                'foreign_keys': [
                    {
                        'name': fk.name,
                        'column': fk.column,
                        'referenced_table': fk.referenced_table,
                        'referenced_column': fk.referenced_column,
                        'on_delete': fk.on_delete,
                        'on_update': fk.on_update
                    }
                    for fk in table.foreign_keys
                ],
                'indexes': [
                    {
                        'name': idx.name,
                        'columns': idx.columns,
                        'is_unique': idx.is_unique,
                        'is_clustered': idx.is_clustered,
                        'filter_condition': idx.filter_condition
                    }
                    for idx in table.indexes
                ],
                'constraints': [
                    {
                        'name': const.name,
                        'constraint_type': const.constraint_type,
                        'definition': const.definition,
                        'columns': const.columns
                    }
                    for const in table.constraints
                ]
            }
            schema_dict['tables'][table_name] = table_dict
        
        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(schema_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully exported {len(schema.tables)} tables to JSON")
    
    def export_to_markdown(self, schema: DatabaseSchema, output_path: str) -> None:
        """
        Export schema documentation to Markdown format.
        
        Args:
            schema: DatabaseSchema object to document
            output_path: Path where Markdown file will be written
            
        Raises:
            IOError: If file cannot be written
        """
        logger.info(f"Exporting schema documentation to Markdown: {output_path}")
        
        # Filter to structured data tables only
        structured_tables = self._filter_structured_data_tables(schema)
        
        lines = []
        lines.append("# Database Schema Documentation")
        lines.append("")
        
        # Metadata
        if schema.source_file:
            lines.append(f"**Source:** {schema.source_file}")
        if schema.extracted_at:
            lines.append(f"**Extracted:** {schema.extracted_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Version:** {schema.version}")
        lines.append(f"**Total Tables:** {len(structured_tables)}")
        lines.append("")
        
        # Table of contents
        lines.append("## Tables")
        lines.append("")
        for table_name in sorted(structured_tables.keys()):
            lines.append(f"- [{table_name}](#{table_name.lower().replace('_', '-')})")
        lines.append("")
        
        # Table details
        for table_name in sorted(structured_tables.keys()):
            table = structured_tables[table_name]
            lines.append(f"## {table_name}")
            lines.append("")
            
            # Columns table
            lines.append("### Columns")
            lines.append("")
            lines.append("| Column | Type | Nullable | Default | Notes |")
            lines.append("|--------|------|----------|---------|-------|")
            
            for col in table.columns:
                # Build type string
                type_str = col.data_type
                if col.max_length:
                    type_str += f"({col.max_length})"
                elif col.precision and col.scale is not None:
                    type_str += f"({col.precision},{col.scale})"
                elif col.precision:
                    type_str += f"({col.precision})"
                
                nullable = "Yes" if col.nullable else "No"
                default = col.default_value if col.default_value else ""
                
                notes = []
                if col.is_identity:
                    notes.append("IDENTITY")
                if table.primary_key and col.name in table.primary_key:
                    notes.append("PK")
                notes_str = ", ".join(notes)
                
                lines.append(f"| {col.name} | {type_str} | {nullable} | {default} | {notes_str} |")
            
            lines.append("")
            
            # Primary key
            if table.primary_key:
                lines.append("### Primary Key")
                lines.append("")
                lines.append(f"- {', '.join(table.primary_key)}")
                lines.append("")
            
            # Foreign keys
            if table.foreign_keys:
                lines.append("### Foreign Keys")
                lines.append("")
                for fk in table.foreign_keys:
                    fk_desc = f"- **{fk.name}**: {fk.column} → {fk.referenced_table}.{fk.referenced_column}"
                    if fk.on_delete:
                        fk_desc += f" (ON DELETE {fk.on_delete})"
                    if fk.on_update:
                        fk_desc += f" (ON UPDATE {fk.on_update})"
                    lines.append(fk_desc)
                lines.append("")
            
            # Indexes
            if table.indexes:
                lines.append("### Indexes")
                lines.append("")
                for idx in table.indexes:
                    idx_type = []
                    if idx.is_unique:
                        idx_type.append("UNIQUE")
                    if idx.is_clustered:
                        idx_type.append("CLUSTERED")
                    idx_type_str = " ".join(idx_type) if idx_type else "NONCLUSTERED"
                    
                    idx_desc = f"- **{idx.name}** ({idx_type_str}): {', '.join(idx.columns)}"
                    if idx.filter_condition:
                        idx_desc += f" WHERE {idx.filter_condition}"
                    lines.append(idx_desc)
                lines.append("")
            
            # Constraints
            if table.constraints:
                lines.append("### Constraints")
                lines.append("")
                for const in table.constraints:
                    lines.append(f"- **{const.name}** ({const.constraint_type}): {const.definition}")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Successfully exported documentation for {len(structured_tables)} tables to Markdown")
    
    def _filter_structured_data_tables(self, schema: DatabaseSchema) -> Dict[str, TableSchema]:
        """
        Filter schema to include only structured data tables.
        
        Excludes standard news article tables:
        - news_articles
        - news_sources
        - keywords
        - article_keywords
        - scraping_logs
        
        Args:
            schema: DatabaseSchema object to filter
            
        Returns:
            Dictionary of table name to TableSchema for structured data tables only
        """
        return schema.get_structured_data_tables()
