"""
Script to run database schema on Azure SQL Database - Version 2
Executes SQL statements one by one with proper batch handling
"""
import pyodbc
import os
import re

def get_connection_string():
    """Get database connection string"""
    print("Connecting to Azure SQL Database using Azure CLI...")
    return "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Authentication=ActiveDirectoryInteractive;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

def parse_sql_file(sql_content):
    """Parse SQL file into individual executable statements"""
    # Remove all comments first
    lines = []
    for line in sql_content.split('\n'):
        # Remove inline comments
        if '--' in line:
            line = line[:line.index('--')]
        line = line.strip()
        if line:
            lines.append(line)
    
    # Join all lines
    full_sql = ' '.join(lines)
    
    # Now we need to intelligently split this
    # Strategy: Find major DDL statements and split there
    statements = []
    current = []
    
    # Split by semicolons first
    parts = full_sql.split(';')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Check if this starts a new major statement
        if re.match(r'^\s*(CREATE\s+(TABLE|VIEW|PROCEDURE|INDEX)|INSERT\s+INTO|ALTER\s+TABLE)', part, re.IGNORECASE):
            # Save previous statement if exists
            if current:
                statements.append(' '.join(current))
                current = []
        
        current.append(part)
    
    # Add last statement
    if current:
        statements.append(' '.join(current))
    
    return statements

def execute_statement(cursor, conn, statement):
    """Execute a single SQL statement"""
    try:
        cursor.execute(statement)
        conn.commit()
        return True, None
    except pyodbc.Error as e:
        error_str = str(e)
        # Check if it's a "already exists" error
        if any(x in error_str for x in ['already an object', 'already exists', 'There is already']):
            return None, "exists"
        return False, str(e)

def run_schema():
    """Run database schema SQL file"""
    conn_str = get_connection_string()
    
    try:
        # Read schema file
        schema_file = os.path.join(os.path.dirname(__file__), 'shared', 'database_schema.sql')
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        print("Read schema file successfully!")
        
        # Parse into statements
        statements = parse_sql_file(schema_sql)
        print(f"Found {len(statements)} SQL statements to execute\n")
        
        # Connect to database
        print("Connecting to database...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print("Connected successfully!\n")
        
        # Execute each statement
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, stmt in enumerate(statements, 1):
            if not stmt.strip():
                continue
            
            # Get statement type for display
            stmt_type = "SQL"
            if re.match(r'^\s*CREATE\s+TABLE', stmt, re.IGNORECASE):
                stmt_type = "CREATE TABLE"
            elif re.match(r'^\s*CREATE\s+VIEW', stmt, re.IGNORECASE):
                stmt_type = "CREATE VIEW"
            elif re.match(r'^\s*CREATE\s+PROCEDURE', stmt, re.IGNORECASE):
                stmt_type = "CREATE PROCEDURE"
            elif re.match(r'^\s*CREATE\s+INDEX', stmt, re.IGNORECASE):
                stmt_type = "CREATE INDEX"
            elif re.match(r'^\s*INSERT\s+INTO', stmt, re.IGNORECASE):
                stmt_type = "INSERT"
            
            print(f"[{i}/{len(statements)}] Executing {stmt_type}...", end=" ")
            
            result, error = execute_statement(cursor, conn, stmt)
            
            if result is True:
                success_count += 1
                print("✓ Success")
            elif result is None:
                skip_count += 1
                print("⊘ Skipped (already exists)")
            else:
                error_count += 1
                print(f"✗ Error")
                print(f"    Error: {error[:150]}")
                print(f"    Statement: {stmt[:150]}...")
        
        cursor.close()
        conn.close()
        
        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  ✓ Successful: {success_count}")
        print(f"  ⊘ Skipped: {skip_count}")
        print(f"  ✗ Errors: {error_count}")
        print(f"  Total: {len(statements)}")
        print(f"{'='*60}")
        
        if error_count == 0:
            print("\n✓ Database schema setup completed successfully!")
            return True
        else:
            print(f"\n⚠ Database schema setup completed with {error_count} errors")
            return False
        
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_schema()
    exit(0 if success else 1)
