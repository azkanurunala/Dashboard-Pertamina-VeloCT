import os
import json
import pyodbc


def load_conn_str() -> str:
    """Load SQL connection string from env var or local.settings.json Values."""
    conn = os.getenv("SQL_SERVER_CONNECTION_STRING")
    if not conn:
        settings_path = os.path.join(os.path.dirname(__file__), "local.settings.json")
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                conn = json.load(f).get("Values", {}).get("SQL_SERVER_CONNECTION_STRING")
    if not conn:
        raise RuntimeError(
            "SQL_SERVER_CONNECTION_STRING is not set "
            "(env var or local.settings.json Values.SQL_SERVER_CONNECTION_STRING)."
        )
    return conn


try:
    print("Loading SQL connection string from env/local.settings.json...")
    conn_str = load_conn_str()

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
