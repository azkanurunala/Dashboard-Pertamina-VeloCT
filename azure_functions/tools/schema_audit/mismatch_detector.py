"""
Mismatch Detector for Database Schema Audit System.

This module compares reference database schemas (from BACPAC) with schemas
used in code to identify discrepancies in table names, column names, data types,
and other schema attributes.
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import logging

from .models import (
    DatabaseSchema,
    TableSchema,
    ColumnSchema,
    TableOperation,
    Mismatch,
    MismatchType,
    Severity,
    CodeLocation,
    OperationType
)

logger = logging.getLogger(__name__)


@dataclass
class CodeSchemaMap:
    """
    Represents schema information extracted from code.
    Maps table names to operations and column usage.
    """
    table_operations: Dict[str, List[TableOperation]] = field(default_factory=dict)
    
    def get_tables(self) -> Set[str]:
        """Get all table names found in code"""
        return set(self.table_operations.keys())
    
    def get_columns_for_table(self, table_name: str) -> Set[str]:
        """Get all columns used for a specific table"""
        columns = set()
        if table_name in self.table_operations:
            for operation in self.table_operations[table_name]:
                columns.update(operation.columns)
        return columns
    
    def get_operations_for_table(self, table_name: str) -> List[TableOperation]:
        """Get all operations for a specific table"""
        return self.table_operations.get(table_name, [])


class MismatchDetector:
    """
    Detects mismatches between reference database schema and code usage.
    
    Compares:
    - Table existence
    - Column names
    - Column data types
    - Column attributes (nullable, defaults, etc.)
    """
    
    def __init__(self, reference_schema: DatabaseSchema):
        """
        Initialize mismatch detector with reference schema.
        
        Args:
            reference_schema: The authoritative schema from BACPAC
        """
        self.reference_schema = reference_schema
        self.mismatches: List[Mismatch] = []
        logger.info(f"Initialized MismatchDetector with {len(reference_schema.tables)} reference tables")
    
    def compare_schemas(self, code_schema: CodeSchemaMap) -> List[Mismatch]:
        """
        Compare reference schema with code usage and detect all mismatches.
        
        Args:
            code_schema: Schema information extracted from code
            
        Returns:
            List of all detected mismatches
        """
        logger.info("Starting schema comparison")
        self.mismatches = []
        
        # Detect table-level mismatches
        self._detect_missing_tables(code_schema)
        self._detect_extra_tables(code_schema)
        
        # Detect column-level mismatches for tables that exist in both
        reference_tables = set(self.reference_schema.tables.keys())
        code_tables = code_schema.get_tables()
        common_tables = reference_tables.intersection(code_tables)
        
        for table_name in common_tables:
            self._detect_column_mismatches(table_name, code_schema)
        
        logger.info(f"Schema comparison complete. Found {len(self.mismatches)} mismatches")
        return self.mismatches
    
    def detect_missing_tables(self, code_schema: CodeSchemaMap) -> List[Mismatch]:
        """
        Find tables used in code but not present in reference schema.
        
        Args:
            code_schema: Schema information from code
            
        Returns:
            List of MISSING_TABLE mismatches
        """
        self.mismatches = []
        self._detect_missing_tables(code_schema)
        return [m for m in self.mismatches if m.mismatch_type == MismatchType.MISSING_TABLE]
    
    def detect_column_mismatches(self, table_name: str, code_schema: CodeSchemaMap) -> List[Mismatch]:
        """
        Find column-level mismatches for a specific table.
        
        Args:
            table_name: Name of table to check
            code_schema: Schema information from code
            
        Returns:
            List of column-related mismatches
        """
        temp_mismatches = []
        self.mismatches = []
        self._detect_column_mismatches(table_name, code_schema)
        temp_mismatches = self.mismatches
        self.mismatches = []
        return temp_mismatches
    
    def _detect_missing_tables(self, code_schema: CodeSchemaMap) -> None:
        """
        Internal method to detect tables in code but not in reference.
        
        Adds MISSING_TABLE mismatches to self.mismatches.
        """
        reference_tables = set(t.lower() for t in self.reference_schema.tables.keys())
        code_tables = code_schema.get_tables()
        
        for table_name in code_tables:
            if table_name.lower() not in reference_tables:
                # Collect all locations where this table is used
                operations = code_schema.get_operations_for_table(table_name)
                locations = [op.location for op in operations]
                
                mismatch = Mismatch(
                    mismatch_type=MismatchType.MISSING_TABLE,
                    severity=Severity.CRITICAL,
                    table_name=table_name,
                    expected_value="Table should exist in reference schema",
                    actual_value=f"Table '{table_name}' not found in reference",
                    locations=locations,
                    fix_suggestion=f"Verify table name or add '{table_name}' to reference schema"
                )
                self.mismatches.append(mismatch)
                logger.warning(f"Missing table detected: {table_name}")
    
    def _detect_extra_tables(self, code_schema: CodeSchemaMap) -> None:
        """
        Internal method to detect tables in reference but not used in code.
        
        Adds EXTRA_TABLE mismatches to self.mismatches.
        """
        reference_tables = set(t.lower() for t in self.reference_schema.tables.keys())
        code_tables_lower = set(t.lower() for t in code_schema.get_tables())
        
        for table_name in self.reference_schema.tables.keys():
            if table_name.lower() not in code_tables_lower:
                mismatch = Mismatch(
                    mismatch_type=MismatchType.EXTRA_TABLE,
                    severity=Severity.INFO,
                    table_name=table_name,
                    expected_value=f"Table '{table_name}' should be used in code",
                    actual_value="Table not referenced in any code",
                    locations=[],
                    fix_suggestion=f"Consider using table '{table_name}' or remove from schema"
                )
                self.mismatches.append(mismatch)
                logger.info(f"Extra table detected: {table_name}")

    
    def _detect_column_mismatches(self, table_name: str, code_schema: CodeSchemaMap) -> None:
        """
        Internal method to detect column-level mismatches for a table.
        
        Checks for:
        - Missing columns (in code but not in reference)
        - Extra columns (in reference but not in code)
        - Column name mismatches
        - Column type mismatches
        - Column attribute mismatches
        
        Args:
            table_name: Name of table to check
            code_schema: Schema information from code
        """
        # Get reference table (case-insensitive)
        ref_table = self.reference_schema.get_table(table_name)
        if not ref_table:
            logger.warning(f"Table '{table_name}' not found in reference schema")
            return
        
        # Get columns used in code
        code_columns = code_schema.get_columns_for_table(table_name)
        ref_columns = {col.name.lower(): col for col in ref_table.columns}
        
        # Check for missing columns (in code but not in reference)
        for code_col_name in code_columns:
            if code_col_name.lower() not in ref_columns:
                operations = code_schema.get_operations_for_table(table_name)
                locations = [
                    op.location for op in operations 
                    if code_col_name in op.columns
                ]
                
                mismatch = Mismatch(
                    mismatch_type=MismatchType.MISSING_COLUMN,
                    severity=Severity.CRITICAL,
                    table_name=table_name,
                    column_name=code_col_name,
                    expected_value=f"Column should exist in table '{table_name}'",
                    actual_value=f"Column '{code_col_name}' not found in reference",
                    locations=locations,
                    fix_suggestion=f"Verify column name or add '{code_col_name}' to table '{table_name}'"
                )
                self.mismatches.append(mismatch)
                logger.warning(f"Missing column: {table_name}.{code_col_name}")
        
        # Check for extra columns (in reference but not in code)
        code_columns_lower = set(col.lower() for col in code_columns)
        for ref_col_name, ref_col in ref_columns.items():
            if ref_col_name not in code_columns_lower:
                # Get operations for this table to provide context
                operations = code_schema.get_operations_for_table(table_name)
                locations = [op.location for op in operations]
                
                mismatch = Mismatch(
                    mismatch_type=MismatchType.EXTRA_COLUMN,
                    severity=Severity.WARNING,
                    table_name=table_name,
                    column_name=ref_col.name,
                    expected_value=f"Column '{ref_col.name}' should be used in code",
                    actual_value="Column not referenced in any operation",
                    locations=locations,
                    fix_suggestion=f"Add column '{ref_col.name}' to operations or remove from schema"
                )
                self.mismatches.append(mismatch)
                logger.info(f"Extra column: {table_name}.{ref_col.name}")
        
        # For columns that exist in both, check types and attributes
        for code_col_name in code_columns:
            if code_col_name.lower() in ref_columns:
                ref_col = ref_columns[code_col_name.lower()]
                self._compare_column_types(table_name, code_col_name, ref_col, code_schema)
                self._compare_column_attributes(table_name, code_col_name, ref_col, code_schema)
    
    def _compare_column_types(
        self, 
        table_name: str, 
        column_name: str, 
        ref_column: ColumnSchema,
        code_schema: CodeSchemaMap
    ) -> None:
        """
        Compare column data types between reference and code usage.
        
        Note: This is a placeholder for type checking. In practice, type information
        is often not available from code analysis (INSERT statements don't specify types).
        This method can be extended when CREATE TABLE statements are analyzed.
        
        Args:
            table_name: Name of the table
            column_name: Name of the column
            ref_column: Reference column schema
            code_schema: Code schema information
        """
        # Type checking would require analyzing CREATE TABLE statements
        # For now, we log that type checking is limited
        logger.debug(f"Type checking for {table_name}.{column_name}: {ref_column.data_type}")
        
        # Future enhancement: Parse CREATE TABLE statements and compare types
        # This would detect mismatches like VARCHAR(50) vs VARCHAR(100)
        # or INT vs BIGINT, etc.
    
    def _compare_column_attributes(
        self,
        table_name: str,
        column_name: str,
        ref_column: ColumnSchema,
        code_schema: CodeSchemaMap
    ) -> None:
        """
        Compare column attributes like nullability and defaults.
        
        Note: This is a placeholder for attribute checking. In practice, attribute
        information is often not available from INSERT/UPDATE statements.
        This method can be extended when CREATE TABLE statements are analyzed.
        
        Args:
            table_name: Name of the table
            column_name: Name of the column
            ref_column: Reference column schema
            code_schema: Code schema information
        """
        # Attribute checking would require analyzing CREATE TABLE statements
        # For now, we log that attribute checking is limited
        logger.debug(
            f"Attribute checking for {table_name}.{column_name}: "
            f"nullable={ref_column.nullable}, default={ref_column.default_value}"
        )
        
        # Future enhancement: Parse CREATE TABLE statements and compare attributes
        # This would detect mismatches in:
        # - NOT NULL constraints
        # - DEFAULT values
        # - IDENTITY columns
        # - Max length for VARCHAR/NVARCHAR
    
    def _determine_severity(self, mismatch_type: MismatchType, context: Optional[Dict] = None) -> Severity:
        """
        Determine severity level for a mismatch type.
        
        Severity assignment logic:
        - CRITICAL: Will cause runtime errors (missing table, missing column, type mismatch)
        - WARNING: Potential issues (extra column, unused table)
        - INFO: Informational only (naming conventions, unused reference items)
        
        Args:
            mismatch_type: Type of mismatch detected
            context: Optional context information for severity determination
            
        Returns:
            Severity level for the mismatch
        """
        # Critical mismatches that will cause runtime errors
        critical_types = {
            MismatchType.MISSING_TABLE,      # Table doesn't exist - INSERT will fail
            MismatchType.MISSING_COLUMN,     # Column doesn't exist - INSERT will fail
            MismatchType.COLUMN_TYPE_MISMATCH  # Type mismatch - data corruption risk
        }
        
        # Warning mismatches that indicate potential problems
        warning_types = {
            MismatchType.EXTRA_COLUMN,       # Column not used - incomplete data
            MismatchType.COLUMN_NAME_MISMATCH  # Name differs - possible confusion
        }
        
        # Info mismatches that are informational only
        info_types = {
            MismatchType.EXTRA_TABLE         # Table exists but unused - no impact
        }
        
        if mismatch_type in critical_types:
            return Severity.CRITICAL
        elif mismatch_type in warning_types:
            return Severity.WARNING
        elif mismatch_type in info_types:
            return Severity.INFO
        else:
            # Default to WARNING for unknown types
            logger.warning(f"Unknown mismatch type: {mismatch_type}, defaulting to WARNING")
            return Severity.WARNING
    
    def categorize_by_severity(self, mismatches: Optional[List[Mismatch]] = None) -> Dict[str, List[Mismatch]]:
        """
        Categorize mismatches by severity level.
        
        Args:
            mismatches: List of mismatches to categorize (uses self.mismatches if None)
            
        Returns:
            Dictionary mapping severity level to list of mismatches
        """
        if mismatches is None:
            mismatches = self.mismatches
        
        categorized = {
            'CRITICAL': [],
            'WARNING': [],
            'INFO': []
        }
        
        for mismatch in mismatches:
            categorized[mismatch.severity.value].append(mismatch)
        
        logger.info(
            f"Categorized {len(mismatches)} mismatches: "
            f"CRITICAL={len(categorized['CRITICAL'])}, "
            f"WARNING={len(categorized['WARNING'])}, "
            f"INFO={len(categorized['INFO'])}"
        )
        
        return categorized
    
    def group_by_table(self, mismatches: Optional[List[Mismatch]] = None) -> Dict[str, List[Mismatch]]:
        """
        Group mismatches by table name.
        
        Args:
            mismatches: List of mismatches to group (uses self.mismatches if None)
            
        Returns:
            Dictionary mapping table name to list of mismatches
        """
        if mismatches is None:
            mismatches = self.mismatches
        
        grouped: Dict[str, List[Mismatch]] = {}
        
        for mismatch in mismatches:
            table_name = mismatch.table_name
            if table_name not in grouped:
                grouped[table_name] = []
            grouped[table_name].append(mismatch)
        
        logger.info(f"Grouped {len(mismatches)} mismatches across {len(grouped)} tables")
        
        return grouped
    
    def get_critical_mismatches(self) -> List[Mismatch]:
        """
        Get all critical mismatches that will cause runtime errors.
        
        Returns:
            List of critical mismatches
        """
        return [m for m in self.mismatches if m.severity == Severity.CRITICAL]
    
    def get_summary(self) -> Dict[str, int]:
        """
        Get summary statistics of detected mismatches.
        
        Returns:
            Dictionary with counts by type and severity
        """
        summary = {
            'total': len(self.mismatches),
            'critical': len([m for m in self.mismatches if m.severity == Severity.CRITICAL]),
            'warning': len([m for m in self.mismatches if m.severity == Severity.WARNING]),
            'info': len([m for m in self.mismatches if m.severity == Severity.INFO]),
        }
        
        # Count by type
        for mismatch_type in MismatchType:
            count = len([m for m in self.mismatches if m.mismatch_type == mismatch_type])
            summary[mismatch_type.value.lower()] = count
        
        return summary
    
    def generate_mismatch_report(self, mismatches: Optional[List[Mismatch]] = None) -> str:
        """
        Generate a formatted text report of all mismatches.
        
        Groups mismatches by table and severity, providing a clear overview
        of all schema discrepancies found.
        
        Args:
            mismatches: List of mismatches to report (uses self.mismatches if None)
            
        Returns:
            Formatted text report as a string
        """
        if mismatches is None:
            mismatches = self.mismatches
        
        if not mismatches:
            return "No schema mismatches detected."
        
        # Build report
        lines = []
        lines.append("=" * 80)
        lines.append("SCHEMA MISMATCH REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Summary section
        summary = self.get_summary()
        lines.append(f"Total Mismatches: {summary['total']}")
        lines.append(f"  - CRITICAL: {summary['critical']}")
        lines.append(f"  - WARNING:  {summary['warning']}")
        lines.append(f"  - INFO:     {summary['info']}")
        lines.append("")
        
        # Group by severity
        categorized = self.categorize_by_severity(mismatches)
        
        for severity in ['CRITICAL', 'WARNING', 'INFO']:
            severity_mismatches = categorized[severity]
            if not severity_mismatches:
                continue
            
            lines.append("-" * 80)
            lines.append(f"{severity} MISMATCHES ({len(severity_mismatches)})")
            lines.append("-" * 80)
            lines.append("")
            
            # Group by table within severity
            grouped = {}
            for mismatch in severity_mismatches:
                table = mismatch.table_name
                if table not in grouped:
                    grouped[table] = []
                grouped[table].append(mismatch)
            
            # Report each table's mismatches
            for table_name in sorted(grouped.keys()):
                table_mismatches = grouped[table_name]
                lines.append(f"Table: {table_name}")
                lines.append("")
                
                for mismatch in table_mismatches:
                    lines.append(f"  Type: {mismatch.mismatch_type.value}")
                    if mismatch.column_name:
                        lines.append(f"  Column: {mismatch.column_name}")
                    lines.append(f"  Expected: {mismatch.expected_value}")
                    lines.append(f"  Actual: {mismatch.actual_value}")
                    lines.append(f"  Fix: {mismatch.fix_suggestion}")
                    
                    if mismatch.locations:
                        lines.append(f"  Locations ({len(mismatch.locations)}):")
                        for loc in mismatch.locations[:3]:  # Show first 3 locations
                            lines.append(f"    - {loc.file_path}:{loc.line_number}")
                        if len(mismatch.locations) > 3:
                            lines.append(f"    ... and {len(mismatch.locations) - 3} more")
                    
                    lines.append("")
                
                lines.append("")
        
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        report = "\n".join(lines)
        logger.info(f"Generated mismatch report with {len(mismatches)} mismatches")
        
        return report
