IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_DeduplicateArticles')
    DROP PROCEDURE sp_DeduplicateArticles;
GO

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
    
    RETURN @DeletedCount;
END;
GO
