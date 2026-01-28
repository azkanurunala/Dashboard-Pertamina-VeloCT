"""
Simple database schema setup using SQL file execution
This script will prompt for SQL Server credentials
"""
import pyodbc
import os
import sys

def get_credentials():
    """Get SQL Server credentials from user"""
    print("=" * 60)
    print("Azure SQL Database Setup")
    print("=" * 60)
    print()
    print("Server: pei-dashboard.database.windows.net")
    print("Database: pei-dashboard")
    print()
    
    username = input("Enter SQL Server username (default: CloudSAa33fbc7c): ").strip()
    if not username:
        username = "CloudSAa33fbc7c"
    
    password = input("Enter SQL Server password: ").strip()
    
    return username, password

def execute_sql_file(cursor, conn, sql_file):
    """Execute SQL file with GO statement handling"""
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Split by GO statements
    batches = []
    current_batch = []
    
    for line in sql_content.split('\n'):
        if line.strip().upper() == 'GO':
            if current_batch:
                batches.append('\n'.join(current_batch))
                current_batch = []
        else:
            current_batch.append(line)
    
    # Add last batch
    if current_batch:
        batches.append('\n'.join(current_batch))
    
    print(f"\nFound {len(batches)} SQL batches to execute\n")
    
    success = 0
    errors = 0
    
    for i, batch in enumerate(batches, 1):
        batch = batch.strip()
        if not batch or batch.startswith('--'):
            continue
        
        try:
            print(f"[{i}/{len(batches)}] Executing batch...", end=" ")
            cursor.execute(batch)
            conn.commit()
            print("✓")
            success += 1
        except pyodbc.Error as e:
            error_msg = str(e)
            if 'already exists' in error_msg or 'already an object' in error_msg:
                print("⊘ (already exists)")
            else:
                print(f"✗")
                print(f"  Error: {error_msg[:200]}")
                errors += 1
    
    print(f"\n{'=' * 60}")
    print(f"Summary: {success} successful, {errors} errors")
    print(f"{'=' * 60}")
    
    return errors == 0

def main():
    try:
        # Get credentials
        username, password = get_credentials()
        
        # Build connection string
        conn_str = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:pei-dashboard.database.windows.net,1433;"
            f"Database=pei-dashboard;"
            f"Uid={username};"
            f"Pwd={password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
        
        print("\nConnecting to database...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print("✓ Connected successfully!\n")
        
        # Execute schema file
        schema_file = os.path.join(os.path.dirname(__file__), 'shared', 'database_schema_with_go.sql')
        
        if not os.path.exists(schema_file):
            print(f"✗ Schema file not found: {schema_file}")
            return False
        
        print(f"Executing schema file: {schema_file}\n")
        success = execute_sql_file(cursor, conn, schema_file)
        
        cursor.close()
        conn.close()
        
        if success:
            print("\n✓ Database schema setup completed successfully!")
        else:
            print("\n⚠ Database schema setup completed with some errors")
        
        return success
        
    except pyodbc.Error as e:
        print(f"\n✗ Database connection error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print("\nPress Enter to exit...")
    input()
    sys.exit(0 if success else 1)
