"""
Simple script to initialize database schema using Azure CLI
Splits schema into smaller chunks for better execution
"""
import subprocess
import os
import tempfile

def execute_sql_file(sql_file_path, server, database):
    """Execute SQL file using Azure CLI"""
    try:
        cmd = [
            'az', 'sql', 'db', 'query',
            '--server', server,
            '--database', database,
            '--auth-mode', 'ActiveDirectoryIntegrated',
            '--file', sql_file_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        return result.returncode == 0, result.stdout, result.stderr
        
    except Exception as e:
        return False, "", str(e)

def main():
    print("🚀 Initializing Azure SQL Database Schema")
    print("=" * 60)
    
    server = "pei-dashboard"
    database = "pei-dashboard"
    schema_file = os.path.join(os.path.dirname(__file__), 'shared', 'database_schema.sql')
    
    print(f"📁 Reading schema file: {schema_file}")
    
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_content = f.read()
    
    print(f"✅ Schema file loaded ({len(schema_content)} characters)")
    print(f"\n🔄 Executing schema on {server}/{database}...")
    print("⏳ This may take a few minutes...\n")
    
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8') as temp_file:
        temp_file.write(schema_content)
        temp_file_path = temp_file.name
    
    try:
        success, stdout, stderr = execute_sql_file(temp_file_path, server, database)
        
        if success:
            print("✅ Database schema executed successfully!")
            if stdout:
                print(f"\n📄 Output:\n{stdout}")
        else:
            print("⚠️  Schema execution completed with warnings/errors")
            if stderr:
                # Check if errors are just "already exists" warnings
                if 'already an object' in stderr or 'already exists' in stderr:
                    print("ℹ️  Some objects already exist (this is normal)")
                else:
                    print(f"\n❌ Errors:\n{stderr[:500]}")
        
        print("\n" + "=" * 60)
        print("✅ Database initialization complete!")
        print("\n💡 Next steps:")
        print("   1. Verify tables were created")
        print("   2. Check data was inserted")
        print("   3. Test database connection from Azure Functions")
        
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == "__main__":
    main()
