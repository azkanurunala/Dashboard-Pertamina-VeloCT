"""
Script to run database schema on Azure SQL Database
"""
import pyodbc
import os
import re

def get_connection_string():
    """Get database connection string"""
    print("Connecting to Azure SQL Database using Azure CLI...")
    # Use Azure AD authentication
    return "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Authentication=ActiveDirectoryInteractive;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

def split_sql_batches(sql_content):
    """Split SQL content into executable batches"""
    # Remove comments
    lines = []
    for line in sql_content.split('\n'):
        # Remove inline comments
        if '--' in line:
            line = line[:line.index('--')]
        line = line.strip()
        if line:
            lines.append(line)
    
    sql_content = ' '.join(lines)
    
    # Split by GO statements (case insensitive)
    batches = re.split(r'\bGO\b', sql_content, flags=re.IGNORECASE)
    
    # If no GO statements, split intelligently
    if len(batches) == 1:
        batches = []
        current_batch = []
        
        # Split on CREATE VIEW, CREATE PROCEDURE, and major DDL statements
        statements = sql_content.split(';')
        
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
            
            # Check if this is a CREATE VIEW or CREATE PROCEDURE
            if re.search(r'\bCREATE\s+(VIEW|PROCEDURE)\b', stmt, re.IGNORECASE):
                # Save previous batch if exists
                if current_batch:
                    batches.append('; '.join(current_batch) + ';')
                    current_batch = []
                # This statement becomes its own batch
                batches.append(stmt + ';')
            else:
                current_batch.append(stmt)
        
        # Add remaining statements
        if current_batch:
            batches.append('; '.join(current_batch) + ';')
    
    return [b.strip() for b in batches if b.strip()]

def run_schema():
    """Run database schema SQL file"""
    conn_str = get_connection_string()
    
    try:
        # Read schema file
        schema_file = os.path.join(os.path.dirname(__file__), 'shared', 'database_schema.sql')
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        print("Read schema file successfully!")
        
        # Split into batches
        batches = split_sql_batches(schema_sql)
        print(f"Found {len(batches)} SQL batches to execute")
        
        # Connect to database
        print("Connecting to database...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("Connected to database successfully!")
        
        # Execute each batch
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, batch in enumerate(batches, 1):
            if not batch.strip():
                continue
            
            try:
                print(f"Executing batch {i}/{len(batches)}...")
                cursor.execute(batch)
                conn.commit()
                success_count += 1
                print(f"  Success: Batch {i} executed")
            except pyodbc.Error as e:
                error_str = str(e)
                # Check if error is because object already exists
                if 'already an object' in error_str or 'already exists' in error_str or 'There is already' in error_str:
                    skip_count += 1
                    print(f"  Skipped: Batch {i} (object already exists)")
                else:
                    error_count += 1
                    print(f"  Error in batch {i}: {e}")
                    print(f"    Batch preview: {batch[:200]}...")
        
        cursor.close()
        conn.close()
        
        print(f"\nSummary:")
        print(f"  Successful: {success_count}")
        print(f"  Skipped: {skip_count}")
        print(f"  Errors: {error_count}")
        print(f"  Total batches: {len(batches)}")
        
        if error_count == 0:
            print("\nDatabase schema setup completed successfully!")
        else:
            print(f"\nDatabase schema setup completed with {error_count} errors")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    run_schema()
