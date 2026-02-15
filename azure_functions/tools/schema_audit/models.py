"""
Data models for database schema audit and repair system.

This module defines the core data structures used throughout the schema audit system,
including schema representations, operation tracking, and mismatch detection.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class OperationType(Enum):
    """Types of database operations"""
    CREATE = "CREATE"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SELECT = "SELECT"
    ALTER = "ALTER"


class MismatchType(Enum):
    """Types of schema mismatches"""
    MISSING_TABLE = "MISSING_TABLE"
    EXTRA_TABLE = "EXTRA_TABLE"
    COLUMN_NAME_MISMATCH = "COLUMN_NAME_MISMATCH"
    COLUMN_TYPE_MISMATCH = "COLUMN_TYPE_MISMATCH"
    MISSING_COLUMN = "MISSING_COLUMN"
    EXTRA_COLUMN = "EXTRA_COLUMN"


class Severity(Enum):
    """Severity levels for mismatches"""
    CRITICAL = "CRITICAL"  # Will cause runtime errors
    WARNING = "WARNING"    # Potential issues
    INFO = "INFO"          # Informational only


@dataclass
class ColumnSchema:
    """Schema for a single database column"""
    name: str
    data_type: str
    nullable: bool = True
    default_value: Optional[str] = None
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    is_identity: bool = False

    def validate(self) -> bool:
        """Validate column schema"""
        if not self.name or not self.name.strip():
            return False
        if not self.data_type or not self.data_type.strip():
            return False
        # Validate numeric constraints
        if self.max_length is not None and self.max_length < 0:
            return False
        if self.precision is not None and self.precision < 0:
            return False
        if self.scale is not None and self.scale < 0:
            return False
        return True

    def __eq__(self, other) -> bool:
        """Compare two column schemas for equality"""
        if not isinstance(other, ColumnSchema):
            return False
        return (
            self.name.lower() == other.name.lower() and
            self.data_type.lower() == other.data_type.lower() and
            self.nullable == other.nullable and
            self.max_length == other.max_length and
            self.precision == other.precision and
            self.scale == other.scale
        )


@dataclass
class ForeignKeySchema:
    """Schema for a foreign key constraint"""
    name: str
    column: str
    referenced_table: str
    referenced_column: str
    on_delete: Optional[str] = None
    on_update: Optional[str] = None

    def validate(self) -> bool:
        """Validate foreign key schema"""
        if not all([self.name, self.column, self.referenced_table, self.referenced_column]):
            return False
        return True


@dataclass
class IndexSchema:
    """Schema for a database index"""
    name: str
    columns: List[str]
    is_unique: bool = False
    is_clustered: bool = False
    filter_condition: Optional[str] = None

    def validate(self) -> bool:
        """Validate index schema"""
        if not self.name or not self.name.strip():
            return False
        if not self.columns or len(self.columns) == 0:
            return False
        return True


@dataclass
class ConstraintSchema:
    """Schema for a table constraint"""
    name: str
    constraint_type: str  # CHECK, UNIQUE, DEFAULT, etc.
    definition: str
    columns: List[str] = field(default_factory=list)

    def validate(self) -> bool:
        """Validate constraint schema"""
        if not all([self.name, self.constraint_type, self.definition]):
            return False
        return True


@dataclass
class TableSchema:
    """Schema for a single database table"""
    name: str
    columns: List[ColumnSchema] = field(default_factory=list)
    primary_key: Optional[List[str]] = None
    foreign_keys: List[ForeignKeySchema] = field(default_factory=list)
    indexes: List[IndexSchema] = field(default_factory=list)
    constraints: List[ConstraintSchema] = field(default_factory=list)

    def validate(self) -> bool:
        """Validate table schema"""
        if not self.name or not self.name.strip():
            return False
        if not self.columns:
            return False
        # Validate all columns
        for column in self.columns:
            if not column.validate():
                return False
        # Validate foreign keys
        for fk in self.foreign_keys:
            if not fk.validate():
                return False
        # Validate indexes
        for index in self.indexes:
            if not index.validate():
                return False
        # Validate constraints
        for constraint in self.constraints:
            if not constraint.validate():
                return False
        return True

    def get_column(self, column_name: str) -> Optional[ColumnSchema]:
        """Get column by name (case-insensitive)"""
        for column in self.columns:
            if column.name.lower() == column_name.lower():
                return column
        return None

    def has_column(self, column_name: str) -> bool:
        """Check if table has a column (case-insensitive)"""
        return self.get_column(column_name) is not None


@dataclass
class DatabaseSchema:
    """Complete database schema"""
    tables: Dict[str, TableSchema] = field(default_factory=dict)
    version: str = "1.0"
    extracted_at: Optional[datetime] = None
    source_file: str = ""

    def validate(self) -> bool:
        """Validate database schema"""
        if not self.tables:
            return False
        # Validate all tables
        for table in self.tables.values():
            if not table.validate():
                return False
        return True

    def get_table(self, table_name: str) -> Optional[TableSchema]:
        """Get table by name (case-insensitive)"""
        for name, table in self.tables.items():
            if name.lower() == table_name.lower():
                return table
        return None

    def has_table(self, table_name: str) -> bool:
        """Check if schema has a table (case-insensitive)"""
        return self.get_table(table_name) is not None

    def get_structured_data_tables(self) -> Dict[str, TableSchema]:
        """
        Get only structured data tables (exclude standard news article tables).
        
        Standard news tables to exclude:
        - news_articles
        - news_sources
        - keywords
        - article_keywords
        - scraping_logs
        """
        excluded_tables = {
            'news_articles', 'news_sources', 'keywords', 
            'article_keywords', 'scraping_logs'
        }
        return {
            name: table 
            for name, table in self.tables.items() 
            if name.lower() not in excluded_tables
        }


@dataclass
class CodeLocation:
    """Location in source code"""
    file_path: str
    line_number: int
    function_name: Optional[str] = None
    code_snippet: str = ""

    def validate(self) -> bool:
        """Validate code location"""
        if not self.file_path or not self.file_path.strip():
            return False
        if self.line_number < 1:
            return False
        return True

    def __str__(self) -> str:
        """String representation of code location"""
        func_info = f" in {self.function_name}()" if self.function_name else ""
        return f"{self.file_path}:{self.line_number}{func_info}"


@dataclass
class TableOperation:
    """Database operation found in code"""
    operation_type: OperationType
    table_name: str
    columns: List[str] = field(default_factory=list)
    file_path: str = ""
    line_number: int = 0
    code_snippet: str = ""

    def validate(self) -> bool:
        """Validate table operation"""
        if not self.table_name or not self.table_name.strip():
            return False
        if not self.file_path or not self.file_path.strip():
            return False
        if self.line_number < 1:
            return False
        return True

    @property
    def location(self) -> CodeLocation:
        """Get code location for this operation"""
        return CodeLocation(
            file_path=self.file_path,
            line_number=self.line_number,
            code_snippet=self.code_snippet
        )


@dataclass
class Mismatch:
    """Schema mismatch between reference and code"""
    mismatch_type: MismatchType
    severity: Severity
    table_name: str
    column_name: Optional[str] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    locations: List[CodeLocation] = field(default_factory=list)
    fix_suggestion: str = ""

    def validate(self) -> bool:
        """Validate mismatch"""
        if not self.table_name or not self.table_name.strip():
            return False
        # Validate all locations
        for location in self.locations:
            if not location.validate():
                return False
        return True

    def __str__(self) -> str:
        """String representation of mismatch"""
        parts = [f"[{self.severity.value}] {self.mismatch_type.value}"]
        parts.append(f"Table: {self.table_name}")
        if self.column_name:
            parts.append(f"Column: {self.column_name}")
        if self.expected_value:
            parts.append(f"Expected: {self.expected_value}")
        if self.actual_value:
            parts.append(f"Actual: {self.actual_value}")
        if self.locations:
            parts.append(f"Locations: {len(self.locations)}")
        return " | ".join(parts)


@dataclass
class Fix:
    """Record of a schema fix applied"""
    mismatch: Mismatch
    file_path: str
    line_number: int
    old_code: str
    new_code: str
    applied: bool = False
    error: Optional[str] = None

    def validate(self) -> bool:
        """Validate fix record"""
        if not self.mismatch.validate():
            return False
        if not self.file_path or not self.file_path.strip():
            return False
        if self.line_number < 1:
            return False
        return True


@dataclass
class FixReport:
    """Report of all fixes applied"""
    fixes: List[Fix] = field(default_factory=list)
    total_files_modified: int = 0
    total_fixes_applied: int = 0
    total_fixes_failed: int = 0
    backup_directory: str = ""
    timestamp: Optional[datetime] = None

    def add_fix(self, fix: Fix) -> None:
        """Add a fix to the report"""
        self.fixes.append(fix)
        if fix.applied:
            self.total_fixes_applied += 1
        else:
            self.total_fixes_failed += 1

    def get_modified_files(self) -> List[str]:
        """Get list of all modified files"""
        return list(set(fix.file_path for fix in self.fixes if fix.applied))

    def get_success_rate(self) -> float:
        """Calculate success rate of fixes"""
        total = len(self.fixes)
        if total == 0:
            return 0.0
        return (self.total_fixes_applied / total) * 100


@dataclass
class ValidationResult:
    """Result of a validation check"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    file_path: Optional[str] = None

    def add_error(self, error: str) -> None:
        """Add an error message"""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message"""
        self.warnings.append(warning)

    def __str__(self) -> str:
        """String representation of validation result"""
        status = "VALID" if self.is_valid else "INVALID"
        parts = [f"Status: {status}"]
        if self.file_path:
            parts.append(f"File: {self.file_path}")
        if self.errors:
            parts.append(f"Errors: {len(self.errors)}")
        if self.warnings:
            parts.append(f"Warnings: {len(self.warnings)}")
        return " | ".join(parts)
