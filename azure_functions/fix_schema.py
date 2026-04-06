import pyodbc

try:
    print("Using Azure SQL connection string...")
    conn_str = "Driver={ODBC Driver 18 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    
    print("Connecting to database...")
    conn = pyodbc.connect(conn_str, timeout=15)
    cr = conn.cursor()
    
    print("Checking if articles_scraped column exists in execution_logs...")
    try:
        cr.execute("SELECT articles_scraped FROM execution_logs WHERE 1=0")
        print("Column articles_scraped already exists!")
    except Exception as e:
        if "Invalid column name" in str(e) or "articles_scraped" in str(e):
            print("Adding articles_scraped column...")
            cr.execute("ALTER TABLE execution_logs ADD articles_scraped INT NULL DEFAULT 0;")
            conn.commit()
            print("Column articles_scraped added successfully.")
        else:
            print(f"Other error during check: {e}")
            
    conn.close()
except Exception as e:
    print(f"Fatal Error: {e}")
