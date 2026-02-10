
import os
import pyodbc
from dotenv import load_dotenv

print("Starting direct migration test...")
load_dotenv()

conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=no;TrustServerCertificate=yes;Connection Timeout=30;"

try:
    print("Connecting...")
    conn = pyodbc.connect(conn_str, timeout=10)
    cursor = conn.cursor()
    print("Connected! Attempting to create a test table if not exists...")
    
    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'migration_test_marker')
    BEGIN
        CREATE TABLE migration_test_marker (id INT PRIMARY KEY, created_at DATETIME DEFAULT GETDATE());
    END
    """)
    conn.commit()
    print("Test table created successfully!")
    
    # Now try one of our real tables
    print("Attempting to create biodiesel_hip...")
    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'biodiesel_hip')
    BEGIN
        CREATE TABLE biodiesel_hip (
            id INT IDENTITY(1,1) PRIMARY KEY,
            published_date DATE,
            hip_month NVARCHAR(50),
            price_idr_liter FLOAT,
            scraped_at DATETIME2 DEFAULT GETUTCDATE()
        );
    END
    """)
    conn.commit()
    print("biodiesel_hip created successfully!")
    
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")
