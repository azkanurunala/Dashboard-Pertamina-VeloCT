import os, psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv("NEON_DB_URL"))
conn.autocommit = True
cur = conn.cursor()
sql = open(os.path.join(os.path.dirname(__file__), "create_tables.sql")).read()
cur.execute(sql)
print("Schema created successfully.")
conn.close()
