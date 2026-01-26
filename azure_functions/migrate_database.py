"""
Database migration script - Execute SQL schema
"""
import pyodbc
import os

def migrate_database():
    """Execute database schema migration."""
    print("🗄️ Starting Database Migration")
    print("=" * 50)
    
    connection_string = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=tcp:pei-dashboard.database.windows.net,1433;"
        "Database=pei-dashboard;"
        "Authentication=ActiveDirectoryInteractive;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=60;"
    )
    
    try:
        print("🔐 Connecting to database...")
        connection = pyodbc.connect(connection_string, timeout=60)
        cursor = connection.cursor()
        print("✅ Connected successfully!")
        
        # Read schema file
        schema_file = os.path.join(os.path.dirname(__file__), 'shared', 'database_schema.sql')
        if not os.path.exists(schema_file):
            print(f"❌ Schema file not found: {schema_file}")
            return False
        
        print("📖 Reading schema file...")
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        print("📋 Parsing SQL statements...")
        
        # Split into individual statements
        statements = []
        current_statement = ""
        in_comment_block = False
        
        for line in schema_sql.split('\n'):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Handle comment blocks
            if line.startswith('/*'):
                in_comment_block = True
                continue
            if line.endswith('*/'):
                in_comment_block = False
                continue
            if in_comment_block:
                continue
            
            # Skip single line comments
            if line.startswith('--'):
                continue
            
            # Add line to current statement
            current_statement += line + " "
            
            # If line ends with semicolon, we have a complete statement
            if line.endswith(';'):
                statement = current_statement.strip()
                if statement and not statement.startswith('--'):
                    statements.append(statement)
                current_statement = ""
        
        # Add any remaining statement
        if current_statement.strip():
            statement = current_statement.strip()
            if statement and not statement.startswith('--'):
                statements.append(statement)
        
        print(f"📊 Found {len(statements)} SQL statements to execute")
        
        # Execute statements
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements):
            if not statement or len(statement) < 10:  # Skip very short statements
                continue
            
            try:
                # Show progress
                if i % 10 == 0:
                    print(f"   Progress: {i+1}/{len(statements)} statements...")
                
                cursor.execute(statement)
                success_count += 1
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Expected errors (objects already exist)
                if any(keyword in error_msg for keyword in [
                    "already exists", "there is already an object", 
                    "cannot drop", "does not exist", "duplicate"
                ]):
                    skip_count += 1
                    if i < 20:  # Show first few skips
                        print(f"   ⚠️ Skipped (already exists): {statement[:50]}...")
                else:
                    error_count += 1
                    print(f"   ❌ Error in statement {i+1}: {str(e)[:100]}...")
                    if error_count > 10:  # Stop if too many errors
                        print("   ⚠️ Too many errors, stopping...")
                        break
        
        print(f"\n📊 Migration Results:")
        print(f"   ✅ Successfully executed: {success_count} statements")
        print(f"   ⚠️ Skipped (already exist): {skip_count} statements")
        print(f"   ❌ Errors: {error_count} statements")
        
        # Commit changes
        connection.commit()
        print("✅ Changes committed to database")
        
        # Verify migration
        print("\n🔍 Verifying migration...")
        
        # Check tables
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Check views
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS 
            ORDER BY TABLE_NAME
        """)
        views = [row[0] for row in cursor.fetchall()]
        
        # Check stored procedures
        cursor.execute("""
            SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES 
            WHERE ROUTINE_TYPE = 'PROCEDURE'
            ORDER BY ROUTINE_NAME
        """)
        procedures = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Database Objects Created:")
        print(f"   Tables: {len(tables)}")
        print(f"   Views: {len(views)}")
        print(f"   Stored Procedures: {len(procedures)}")
        
        # Check required tables
        required_tables = ['news_sources', 'keywords', 'news_articles', 'sentiment_analyses']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"   ❌ Missing required tables: {', '.join(missing_tables)}")
            return False
        else:
            print(f"   ✅ All required tables present")
        
        # Check initial data
        if 'news_sources' in tables:
            cursor.execute("SELECT COUNT(*) FROM news_sources")
            source_count = cursor.fetchone()[0]
            print(f"   📊 Initial news sources: {source_count}")
        
        if 'keywords' in tables:
            cursor.execute("SELECT COUNT(*) FROM keywords")
            keyword_count = cursor.fetchone()[0]
            print(f"   📊 Initial keywords: {keyword_count}")
        
        connection.close()
        
        print(f"\n🎉 Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

def main():
    """Main function."""
    success = migrate_database()
    
    if success:
        print("\n💡 Next Steps:")
        print("1. Test database: python test_system.py")
        print("2. Deploy Azure Functions code")
        print("3. Configure application settings")
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Check Azure AD authentication")
        print("2. Verify database permissions")
        print("3. Check SQL Server connectivity")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)