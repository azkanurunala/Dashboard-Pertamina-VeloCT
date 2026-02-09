import asyncio
import pyodbc
import os
import sys

# Add parent directory to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from shared.config import config_manager

async def create_stored_procedures():
    print("⏳ Connecting to database...")
    try:
        conn_str = await config_manager.get_database_connection_string()
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        
        procedures = [
            """
            CREATE OR ALTER PROCEDURE sp_GetOrCreateNewsSource
                @name NVARCHAR(100),
                @base_url NVARCHAR(500),
                @country VARCHAR(10) = NULL,
                @language VARCHAR(10) = 'en',
                @category NVARCHAR(50) = NULL
            AS
            BEGIN
                SET NOCOUNT ON;
                DECLARE @source_id INT;
                SELECT @source_id = id FROM news_sources WHERE name = @name;
                IF @source_id IS NULL
                BEGIN
                    INSERT INTO news_sources (name, base_url, country, language, category)
                    VALUES (@name, @base_url, @country, @language, @category);
                    SET @source_id = SCOPE_IDENTITY();
                END
                SELECT @source_id AS source_id;
            END;
            """,
            """
            CREATE OR ALTER PROCEDURE sp_GetOrCreateKeyword
                @keyword NVARCHAR(100),
                @category NVARCHAR(50) = NULL
            AS
            BEGIN
                SET NOCOUNT ON;
                DECLARE @keyword_id INT;
                SELECT @keyword_id = id FROM keywords WHERE keyword = @keyword;
                IF @keyword_id IS NULL
                BEGIN
                    INSERT INTO keywords (keyword, category)
                    VALUES (@keyword, @category);
                    SET @keyword_id = SCOPE_IDENTITY();
                END
                SELECT @keyword_id AS keyword_id;
            END;
            """,
            """
            CREATE OR ALTER PROCEDURE sp_DeduplicateArticles
            AS
            BEGIN
                SET NOCOUNT ON;
                DECLARE @deleted_count INT = 0;
                WITH DuplicateArticles AS (
                    SELECT id, url,
                           ROW_NUMBER() OVER (PARTITION BY url ORDER BY scraped_date ASC) as rn
                    FROM news_articles
                )
                DELETE FROM news_articles 
                WHERE id IN (
                    SELECT id FROM DuplicateArticles WHERE rn > 1
                );
                SET @deleted_count = @@ROWCOUNT;
                SELECT @deleted_count AS deleted_count;
            END;
            """
        ]
        
        for proc in procedures:
            name = proc.split("PROCEDURE")[1].split("(")[0].strip()
            if "@" in name: # fallback for sp_DeduplicateArticles
                 name = proc.split("PROCEDURE")[1].split("AS")[0].strip()
            
            print(f"🛠️ Creating/Updating procedure: {name}...")
            cursor.execute(proc)
            
        print("✅ All stored procedures created successfully!")
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(create_stored_procedures())
