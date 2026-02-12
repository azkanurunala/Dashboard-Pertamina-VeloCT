
import pyodbc
import os

def fix_procedure():
    print("Fixing sp_DeduplicateArticles...")
    # Hardcoded connection string from previous success
    conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=no;TrustServerCertificate=yes;Connection Timeout=30;"
    
    sql_drop = "IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_DeduplicateArticles') DROP PROCEDURE sp_DeduplicateArticles"
    
    sql_create = """
    CREATE PROCEDURE sp_DeduplicateArticles
    AS
    BEGIN
        SET NOCOUNT ON;
        
        DECLARE @DeletedCount INT;
        
        -- Delete duplicates keeping the oldest record based on URL
        WITH CTE AS (
            SELECT 
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY url 
                    ORDER BY published_date ASC, id ASC
                ) AS rn
            FROM news_articles
            WHERE url IS NOT NULL AND url != ''
        )
        DELETE FROM CTE WHERE rn > 1;
        
        SET @DeletedCount = @@ROWCOUNT;
        
        SELECT @DeletedCount as deleted_count;
    END
    """
    
    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        
        print("Dropping existing procedure...")
        cursor.execute(sql_drop)
        
        print("Creating new procedure...")
        cursor.execute(sql_create)
        
        print("Procedure created successfully.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_procedure()
