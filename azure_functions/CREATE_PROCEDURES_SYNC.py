import pyodbc

conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=no;TrustServerCertificate=yes;Connection Timeout=30;"

def create_procedures():
    print("Connecting...")
    try:
        conn = pyodbc.connect(conn_str, autocommit=True, timeout=10)
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
            print("Creating procedure...")
            cursor.execute(proc)
            
        print("Success!")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_procedures()
