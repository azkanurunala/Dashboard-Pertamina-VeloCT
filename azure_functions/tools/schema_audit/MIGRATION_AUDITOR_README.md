# Migration Auditor

The Migration Auditor is a component of the Database Schema Audit system that scans, audits, and fixes migration scripts to ensure they match the reference database schema.

## Features

- **Scan Migration Scripts**: Automatically finds SQL and Python migration scripts in a directory
- **Audit Operations**: Extracts CREATE TABLE, ALTER TABLE, and other schema operations from scripts
- **Detect Mismatches**: Compares migration operations against reference schema
- **Fix Scripts**: Automatically corrects schema mismatches in migration scripts
- **Generate Migrations**: Creates new migration scripts from table schemas
- **Compatibility Checking**: Simulates migration execution to detect conflicts

## Usage

### Basic Usage

```python
from azure_functions.tools.schema_audit.migration_auditor import MigrationAuditor
from azure_functions.tools.schema_audit.models import DatabaseSchema

# Initialize with reference schema
reference_schema = DatabaseSchema()
# ... populate reference_schema ...

auditor = MigrationAuditor(reference_schema=reference_schema)

# Scan for migration scripts
scripts = auditor.scan_migration_scripts('azure_functions/scripts')
print(f"Found {len(scripts)} migration scripts")

# Audit operations in all scripts
operations = auditor.audit_migration_operations()
print(f"Found {len(operations)} database operations")

# Check compatibility
compat_result = auditor.check_migration_compatibility()
if compat_result['compatible']:
    print("✓ All migrations are compatible")
else:
    print(f"✗ Found {len(compat_result['issues'])} compatibility issues")
```

### Fixing Migration Scripts

```python
# Fix a specific migration script (dry run first)
fix_result = auditor.fix_migration_schema(
    'azure_functions/scripts/migrate_table.sql',
    dry_run=True
)

print(f"Would apply {len(fix_result['changes'])} changes")

# Apply fixes
fix_result = auditor.fix_migration_schema(
    'azure_functions/scripts/migrate_table.sql',
    dry_run=False
)

if fix_result['fixed']:
    print("✓ Migration script fixed successfully")
```

### Generating New Migrations

```python
from azure_functions.tools.schema_audit.models import TableSchema, ColumnSchema

# Define table schema
table_schema = TableSchema(
    name="data_new_table",
    columns=[
        ColumnSchema(name="id", data_type="INT", nullable=False, is_identity=True),
        ColumnSchema(name="name", data_type="NVARCHAR", max_length=100, nullable=False),
        ColumnSchema(name="value", data_type="FLOAT", nullable=True)
    ],
    primary_key=["id"]
)

# Generate SQL migration
auditor.generate_new_migration(
    table_schema,
    'azure_functions/scripts/migrate_new_table.sql',
    migration_type='create'
)

# Generate Python migration
auditor.generate_new_migration(
    table_schema,
    'azure_functions/scripts/migrate_new_table.py',
    migration_type='create'
)
```

### Compatibility Report

```python
# Check compatibility
compat_result = auditor.check_migration_compatibility()

# Generate human-readable report
report = auditor.get_compatibility_report(compat_result)
print(report)

# Or save to file
with open('migration_compatibility_report.md', 'w') as f:
    f.write(report)
```

## Supported Migration Patterns

### SQL Migrations

The auditor can parse:
- `CREATE TABLE` statements
- `ALTER TABLE` statements (ADD COLUMN, DROP COLUMN, etc.)
- `DROP TABLE` statements
- `sp_rename` (SQL Server table renames)

Example:
```sql
CREATE TABLE data_test (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    value FLOAT
);

ALTER TABLE data_test ADD new_column VARCHAR(50);
```

### Python Migrations

The auditor can extract SQL from Python migration scripts:

Example:
```python
import asyncio
from shared.database_handler import DatabaseHandler

async def migrate():
    query = """
    CREATE TABLE data_test (
        id INT PRIMARY KEY,
        name VARCHAR(100)
    )
    """
    # Execute query
    pass
```

## Compatibility Checking

The compatibility checker:
1. Verifies all tables in migrations exist in reference schema
2. Checks column definitions match reference schema
3. Simulates migration execution to detect conflicts
4. Reports issues by severity (error, warning, info)

### Compatibility Result Structure

```python
{
    'compatible': bool,  # Overall compatibility status
    'issues': [          # Critical issues
        {
            'type': str,
            'severity': str,
            'table': str,
            'column': str,
            'location': str,
            'message': str
        }
    ],
    'warnings': [        # Non-critical warnings
        # Same structure as issues
    ],
    'summary': {
        'total_scripts': int,
        'total_operations': int,
        'tables_created': int,
        'tables_altered': int,
        'mismatches_found': int
    }
}
```

## Requirements

Implements requirements:
- **8.1**: Scan migration scripts
- **8.2**: Audit migration operations
- **8.3**: Fix migration schema
- **8.4**: Check migration compatibility
- **8.5**: Generate new migrations

## Limitations

- SQL parsing is regex-based and may not handle all complex SQL syntax
- Complex IF/ELSE blocks in SQL may cause parsing issues
- Dynamic SQL (constructed at runtime) cannot be analyzed
- Python migrations must have SQL in string literals

## Testing

Run tests with:
```bash
pytest azure_functions/tools/schema_audit/test_migration_auditor_basic.py -v
pytest azure_functions/tools/schema_audit/test_migration_auditor_integration.py -v
```
