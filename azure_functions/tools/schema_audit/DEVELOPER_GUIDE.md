# Developer Guide: Database Schema Audit Tool

This guide provides comprehensive information for developers who want to understand, maintain, or extend the Database Schema Audit Tool.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Component Details](#component-details)
- [Data Models](#data-models)
- [Extension Points](#extension-points)
- [Testing Strategy](#testing-strategy)
- [Code Style Guidelines](#code-style-guidelines)
- [Contributing](#contributing)
- [Performance Considerations](#performance-considerations)

## Architecture Overview

### High-Level Architecture

The tool follows a modular pipeline architecture:

```
┌─────────────────┐
│ pei-dashboard   │
│   .bacpac       │──┐
└─────────────────┘  │
                     │ Extract
                     ▼
              ┌──────────────┐
              │   Schema     │
              │  Extractor   │
              └──────┬───────┘
                     │
                     ▼
              ┌──────────────┐
              │  Reference   │
              │   Schema     │
              └──────┬───────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   ┌────────┐  ┌─────────┐  ┌─────────┐
   │  Code  │  │Migration│  │Database │
   │ Auditor│  │ Auditor │  │ Handler │
   │        │  │         │  │ Auditor │
   └────┬───┘  └────┬────┘  └────┬────┘
        │           │            │
        └───────────┼────────────┘
                    │
                    ▼
             ┌──────────────┐
             │  Mismatch    │
             │  Detector    │
             └──────┬───────┘
                    │
                    ▼
             ┌──────────────┐
             │   Schema     │
             │   Fixer      │
             └──────┬───────┘
                    │
                    ▼
             ┌──────────────┐
             │  Validator   │
             │  & Reporter  │
             └──────────────┘
```

### Design Principles

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Immutability**: Data models are immutable dataclasses
3. **Fail-Safe**: Extensive backup and rollback mechanisms
4. **Testability**: All components are independently testable
5. **Extensibility**: Plugin architecture for custom fixers and validators

### Component Interaction Flow

```
User Input (CLI)
    │
    ▼
┌─────────────────────────────────────┐
│  CLI Interface / Main Orchestrator  │
└──────────────┬──────────────────────┘
               │
               ├──► Schema Extractor ──► Reference Schema (JSON)
               │
               ├──► Code Auditor ──► Code Schema Map
               │
               ├──► Mismatch Detector ──► Mismatch Report
               │
               ├──► Schema Fixer ──► Modified Files + Backup
               │
               └──► Validator & Reporter ──► Final Report
```

## Component Details

### 1. Schema Extractor (`schema_extractor.py`)

**Purpose**: Extract database schema from BACPAC files.

**Key Classes**:
- `SchemaExtractor`: Main extraction logic

**Key Methods**:
```python
def extract_from_bacpac(self, bacpac_path: str) -> DatabaseSchema:
    """Extract schema from BACPAC file."""
    
def parse_dacpac_xml(self, xml_content: str) -> DatabaseSchema:
    """Parse DacPac XML model."""
    
def export_to_json(self, schema: DatabaseSchema, output_path: str) -> None:
    """Export schema to JSON format."""
```

**Implementation Details**:
- BACPAC files are ZIP archives containing `model.xml`
- Uses `zipfile` for extraction
- Uses `xml.etree.ElementTree` for XML parsing
- Filters out standard news article tables

**Extension Points**:
- Add support for other schema formats (SQL scripts, JSON schemas)
- Custom table filtering logic
- Additional export formats (YAML, CSV)

### 2. Code Auditor (`code_auditor.py`)

**Purpose**: Scan Python code for database operations.

**Key Classes**:
- `CodeAuditor`: Main auditing logic

**Key Methods**:
```python
def scan_directory(self, directory: str, patterns: List[str] = None) -> None:
    """Scan directory for database operations."""
    
def extract_table_operations(self, file_path: str) -> List[TableOperation]:
    """Extract CREATE TABLE, INSERT, UPDATE operations."""
    
def build_operation_map(self) -> Dict[str, List[TableOperation]]:
    """Build map of table -> operations."""
```

**Implementation Details**:
- Uses Python `ast` module for code parsing
- Identifies SQL operations through pattern matching
- Extracts table and column names from SQL queries
- Records file location and line numbers

**Extension Points**:
- Support for other languages (JavaScript, TypeScript)
- Custom SQL dialect support
- Additional operation types (MERGE, UPSERT)

### 3. Mismatch Detector (`mismatch_detector.py`)

**Purpose**: Compare reference schema with code usage.

**Key Classes**:
- `MismatchDetector`: Main comparison logic
- `CodeSchemaMap`: Represents code schema

**Key Methods**:
```python
def compare_schemas(self, code_schema: CodeSchemaMap) -> List[Mismatch]:
    """Compare reference schema with code usage."""
    
def detect_missing_tables(self) -> List[Mismatch]:
    """Find tables in code but not in reference."""
    
def detect_column_mismatches(self, table_name: str) -> List[Mismatch]:
    """Find column name/type differences."""
    
def categorize_by_severity(self, mismatches: List[Mismatch]) -> Dict[str, List[Mismatch]]:
    """Categorize mismatches by severity."""
```

**Mismatch Types**:
- `MISSING_TABLE`: Table in code not in reference
- `EXTRA_TABLE`: Table in reference not used in code
- `COLUMN_NAME_MISMATCH`: Column name differs
- `COLUMN_TYPE_MISMATCH`: Column type differs
- `MISSING_COLUMN`: Column in reference not in code
- `EXTRA_COLUMN`: Column in code not in reference

**Severity Levels**:
- `CRITICAL`: Will cause runtime errors
- `WARNING`: Potential issues
- `INFO`: Informational only

**Extension Points**:
- Custom mismatch types
- Custom severity rules
- Configurable comparison logic

### 4. Schema Fixer (`schema_fixer.py`)

**Purpose**: Automatically fix schema mismatches.

**Key Classes**:
- `SchemaFixer`: Main fixing logic
- `FixReport`: Results of fix operations

**Key Methods**:
```python
def fix_mismatches(self, mismatches: List[Mismatch], dry_run: bool = False) -> FixReport:
    """Fix all mismatches."""
    
def backup_file(self, file_path: str) -> str:
    """Create backup before modification."""
    
def fix_column_name(self, mismatch: Mismatch) -> bool:
    """Fix column name mismatch."""
```

**Fix Strategies**:
1. **Column Name**: Replace all occurrences with correct name
2. **Column Type**: Update CREATE TABLE statements
3. **Missing Column**: Add to INSERT/UPDATE with default value
4. **Extra Column**: Remove from INSERT/UPDATE operations

**Safety Mechanisms**:
- Automatic backup before modification
- Syntax validation after changes
- Rollback on validation failure
- Dry-run mode for preview

**Extension Points**:
- Custom fix strategies
- Configurable backup locations
- Custom validation rules

### 5. Validator (`validator.py`)

**Purpose**: Validate Python files and schema consistency.

**Key Classes**:
- `Validator`: Main validation logic
- `ValidationResult`: Validation results

**Key Methods**:
```python
def validate_python_syntax(self, file_path: str) -> ValidationResult:
    """Validate Python syntax."""
    
def validate_imports(self, file_path: str) -> ValidationResult:
    """Validate all imports are still valid."""
    
def validate_schema_consistency(self) -> ValidationResult:
    """Validate schema consistency across all files."""
```

**Validation Checks**:
- Python syntax (using `ast.parse`)
- Import resolution
- Schema consistency
- Type annotations (optional)

**Extension Points**:
- Custom validation rules
- Integration with linters (pylint, flake8)
- Custom error messages

### 6. Reporter (`reporter.py`)

**Purpose**: Generate reports and documentation.

**Key Classes**:
- `Reporter`: Main reporting logic

**Key Methods**:
```python
def generate_audit_report(self, mismatches: List[Mismatch]) -> str:
    """Generate audit report in Markdown."""
    
def generate_fix_report(self, fix_report: FixReport) -> str:
    """Generate fix report."""
    
def generate_schema_documentation(self, schema: DatabaseSchema) -> str:
    """Generate schema documentation."""
    
def generate_erd_diagram(self, schema: DatabaseSchema) -> str:
    """Generate ERD in Mermaid format."""
```

**Report Types**:
- Audit reports (mismatches found)
- Fix reports (changes made)
- Schema documentation (table definitions)
- ERD diagrams (relationships)
- Scraper-table mappings

**Extension Points**:
- Additional report formats (HTML, PDF)
- Custom report templates
- Integration with documentation systems

### 7. Model Updater (`model_updater.py`)

**Purpose**: Update models.py and database_handler.py.

**Key Classes**:
- `ModelUpdater`: Main update logic

**Key Methods**:
```python
def update_models_file(self, schema: DatabaseSchema) -> None:
    """Update models.py with new dataclasses."""
    
def update_database_handler(self, schema: DatabaseSchema) -> None:
    """Update database_handler.py with save methods."""
```

**Extension Points**:
- Custom model templates
- Support for ORMs (SQLAlchemy, Django ORM)
- Custom handler patterns

### 8. Migration Auditor (`migration_auditor.py`)

**Purpose**: Audit and fix migration scripts.

**Key Classes**:
- `MigrationAuditor`: Main auditing logic

**Key Methods**:
```python
def scan_migration_scripts(self, directory: str) -> None:
    """Scan for migration scripts."""
    
def audit_migration_operations(self) -> List[TableOperation]:
    """Audit operations in migrations."""
    
def fix_migration_schema(self, mismatches: List[Mismatch]) -> None:
    """Fix schema in migration scripts."""
```

**Extension Points**:
- Support for migration frameworks (Alembic, Flyway)
- Custom migration patterns
- Migration generation

## Data Models

### Core Models (`models.py`)

All data models are immutable dataclasses with type annotations.

#### DatabaseSchema

```python
@dataclass(frozen=True)
class DatabaseSchema:
    """Complete database schema."""
    tables: Dict[str, TableSchema]
    version: str
    extracted_at: datetime
    source_file: str
```

#### TableSchema

```python
@dataclass(frozen=True)
class TableSchema:
    """Schema for a single table."""
    name: str
    columns: List[ColumnSchema]
    primary_key: Optional[List[str]]
    foreign_keys: List[ForeignKeySchema]
    indexes: List[IndexSchema]
    constraints: List[ConstraintSchema]
```

#### ColumnSchema

```python
@dataclass(frozen=True)
class ColumnSchema:
    """Schema for a single column."""
    name: str
    data_type: str
    nullable: bool
    default_value: Optional[str]
    max_length: Optional[int]
    precision: Optional[int]
    scale: Optional[int]
    is_identity: bool
```

#### Mismatch

```python
@dataclass(frozen=True)
class Mismatch:
    """Schema mismatch."""
    mismatch_type: MismatchType
    severity: Severity
    table_name: str
    column_name: Optional[str]
    expected_value: Optional[str]
    actual_value: Optional[str]
    locations: List[CodeLocation]
    fix_suggestion: str
```

### Enumerations

```python
class MismatchType(Enum):
    MISSING_TABLE = "missing_table"
    EXTRA_TABLE = "extra_table"
    COLUMN_NAME_MISMATCH = "column_name_mismatch"
    COLUMN_TYPE_MISMATCH = "column_type_mismatch"
    MISSING_COLUMN = "missing_column"
    EXTRA_COLUMN = "extra_column"

class Severity(Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"
```

## Extension Points

### Adding Custom Fixers

To add a custom fixer for a specific mismatch type:

1. Create a new method in `SchemaFixer`:

```python
def fix_custom_mismatch(self, mismatch: Mismatch) -> bool:
    """Fix custom mismatch type."""
    # Implementation
    return True
```

2. Register the fixer in `fix_mismatches`:

```python
fix_strategies = {
    MismatchType.CUSTOM: self.fix_custom_mismatch,
    # ... other strategies
}
```

### Adding Custom Validators

To add a custom validation rule:

1. Create a new method in `Validator`:

```python
def validate_custom_rule(self, file_path: str) -> ValidationResult:
    """Validate custom rule."""
    # Implementation
    return ValidationResult(is_valid=True, errors=[], warnings=[])
```

2. Call it in `validate_files`:

```python
results.append(self.validate_custom_rule(file_path))
```

### Adding Custom Report Types

To add a new report type:

1. Create a new method in `Reporter`:

```python
def generate_custom_report(self, data: Any) -> str:
    """Generate custom report."""
    # Implementation
    return report_content
```

2. Add to CLI report command in `cli.py`:

```python
elif report_type == 'custom':
    report = reporter.generate_custom_report(data)
```

### Supporting New Schema Formats

To support a new schema format (e.g., JSON schema):

1. Create a new extractor method:

```python
def extract_from_json_schema(self, json_path: str) -> DatabaseSchema:
    """Extract schema from JSON schema file."""
    # Implementation
    return schema
```

2. Add CLI option for the new format

## Testing Strategy

### Test Organization

```
tests/
├── unit/                      # Unit tests
│   ├── test_schema_extractor.py
│   ├── test_code_auditor.py
│   └── ...
├── integration/               # Integration tests
│   ├── test_full_workflow.py
│   └── test_fix_integration.py
└── property/                  # Property-based tests
    ├── test_properties.py
    └── ...
```

### Unit Testing

Unit tests focus on individual components:

```python
def test_extract_column_from_xml():
    """Test column extraction from XML."""
    xml = """<Column Name="id" Type="int" Nullable="false" />"""
    column = extractor._parse_column_definition(xml)
    assert column.name == "id"
    assert column.data_type == "int"
    assert not column.nullable
```

### Integration Testing

Integration tests verify end-to-end workflows:

```python
def test_full_audit_workflow():
    """Test complete audit workflow."""
    cli = SchemaAuditCLI()
    result = cli.run_audit_workflow(
        bacpac_path="test.bacpac",
        code_directory="test_code/"
    )
    assert result['success']
    assert result['total_mismatches'] >= 0
```

### Property-Based Testing

Property tests verify universal properties:

```python
@given(st.text(), st.text())
def test_schema_serialization_roundtrip(table_name, column_name):
    """Schema serialization should preserve all data."""
    schema = create_test_schema(table_name, column_name)
    json_str = schema.to_json()
    restored = DatabaseSchema.from_json(json_str)
    assert schema == restored
```

### Test Coverage Goals

- **Unit tests**: 80% code coverage minimum
- **Integration tests**: All major workflows
- **Property tests**: All correctness properties from design doc

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest test_schema_extractor.py

# With coverage
pytest --cov=. --cov-report=html

# Property tests only
pytest -k "property"

# Integration tests only
pytest -k "integration"
```

## Code Style Guidelines

### Python Style

Follow PEP 8 with these additions:

- **Line length**: 100 characters maximum
- **Imports**: Group by standard library, third-party, local
- **Type hints**: Required for all public methods
- **Docstrings**: Google style for all public classes and methods

### Example

```python
from typing import List, Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    """
    Example class demonstrating code style.
    
    This class shows the preferred code style for the project,
    including type hints, docstrings, and formatting.
    
    Attributes:
        name: The name of the example
        value: The value associated with the example
    """
    name: str
    value: int
    
    def process(self, input_data: List[str]) -> Optional[str]:
        """
        Process input data and return result.
        
        Args:
            input_data: List of strings to process
        
        Returns:
            Processed result or None if processing fails
        
        Raises:
            ValueError: If input_data is empty
        """
        if not input_data:
            raise ValueError("input_data cannot be empty")
        
        # Implementation
        return None
```

### Naming Conventions

- **Classes**: PascalCase (e.g., `SchemaExtractor`)
- **Functions/Methods**: snake_case (e.g., `extract_from_bacpac`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_RETRIES`)
- **Private methods**: Leading underscore (e.g., `_parse_xml`)

### Documentation

- All public classes and methods must have docstrings
- Use Google-style docstrings
- Include type hints in addition to docstrings
- Document exceptions that can be raised

## Contributing

### Development Workflow

1. **Create a branch**: `git checkout -b feature/your-feature`
2. **Make changes**: Implement your feature or fix
3. **Write tests**: Add unit and integration tests
4. **Run tests**: Ensure all tests pass
5. **Update docs**: Update relevant documentation
6. **Submit PR**: Create a pull request with description

### Pull Request Guidelines

- **Title**: Clear, descriptive title
- **Description**: Explain what and why
- **Tests**: Include test coverage
- **Documentation**: Update relevant docs
- **Code style**: Follow style guidelines

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Performance impact considered
- [ ] Security implications reviewed

## Performance Considerations

### Optimization Strategies

1. **Lazy Loading**: Load files only when needed
2. **Caching**: Cache parsed ASTs and schemas
3. **Parallel Processing**: Process files concurrently
4. **Streaming**: Stream large files instead of loading into memory
5. **Indexing**: Build indexes for fast lookups

### Performance Benchmarks

Target performance metrics:

- **Schema extraction**: < 5 seconds for typical BACPAC
- **Code scanning**: < 1 second per file
- **Mismatch detection**: < 10 seconds for 100 tables
- **Fixing**: < 2 seconds per file

### Memory Management

- Use generators for large file lists
- Clear caches periodically
- Limit concurrent file processing
- Stream large XML files

### Profiling

Profile code to identify bottlenecks:

```bash
# Profile with cProfile
python -m cProfile -o profile.stats cli.py audit --bacpac test.bacpac --code test_code/

# Analyze with snakeviz
snakeviz profile.stats
```

## Debugging

### Logging

Enable verbose logging:

```bash
python cli.py audit --bacpac test.bacpac --code test_code/ --verbose
```

### Debug Mode

Set environment variable for debug mode:

```bash
export SCHEMA_AUDIT_DEBUG=1
python cli.py audit --bacpac test.bacpac --code test_code/
```

### Common Debug Scenarios

1. **Schema extraction fails**: Check BACPAC file structure
2. **Code parsing fails**: Check Python syntax
3. **Fixes not applied**: Check file permissions
4. **Validation fails**: Check syntax after fixes

## Additional Resources

- **Design Document**: See `.kiro/specs/database-schema-audit/design.md`
- **Requirements**: See `.kiro/specs/database-schema-audit/requirements.md`
- **Tasks**: See `.kiro/specs/database-schema-audit/tasks.md`
- **User Guide**: See `USER_GUIDE.md`

## Contact

For questions or support, contact the development team or create an issue in the project repository.
