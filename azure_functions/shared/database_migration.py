"""
Database initialization and migration utilities.
Handles schema creation, data migration, and database setup operations.
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

import pyodbc
from .models import DatabaseConfig, NewsArticle, SentimentAnalysis
from .database_handler import DatabaseHandler
from .interfaces import DatabaseError
from .logging_config import get_logger


class DatabaseMigration:
    """
    Handles database schema creation, initialization, and data migration operations.
    """
    
    def __init__(self, config: DatabaseConfig):
        """
        Initialize the database migration handler.
        
        Args:
            config: Database configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.schema_file_path = os.path.join(
            os.path.dirname(__file__), 
            'database_schema.sql'
        )
    
    async def initialize_database(self) -> bool:
        """
        Initialize the database with schema and default data.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Starting database initialization...")
            
            # Check if database exists and is accessible
            if not await self._check_database_connection():
                self.logger.error("Cannot connect to database")
                return False
            
            # Check if schema already exists
            if await self._check_schema_exists():
                self.logger.info("Database schema already exists")
                return True
            
            # Create schema
            await self._create_schema()
            
            # Verify schema creation
            if await self._verify_schema():
                self.logger.info("Database initialization completed successfully")
                return True
            else:
                self.logger.error("Schema verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
            return False
    
    async def _check_database_connection(self) -> bool:
        """Check if database connection is working."""
        try:
            connection = pyodbc.connect(
                self.config.connection_string,
                timeout=self.config.connection_timeout
            )
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            connection.close()
            return result is not None
        except Exception as e:
            self.logger.error(f"Database connection check failed: {str(e)}")
            return False
    
    async def _check_schema_exists(self) -> bool:
        """Check if the required schema already exists."""
        try:
            connection = pyodbc.connect(self.config.connection_string)
            cursor = connection.cursor()
            
            # Check for key tables
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME IN ('news_articles', 'news_sources', 'sentiment_analyses')
            """)
            
            result = cursor.fetchone()
            connection.close()
            
            return result[0] >= 3  # All three main tables should exist
            
        except Exception as e:
            self.logger.warning(f"Schema check failed: {str(e)}")
            return False
    
    async def _create_schema(self) -> None:
        """Create the database schema from SQL file."""
        try:
            # Read schema file
            if not os.path.exists(self.schema_file_path):
                raise DatabaseError(f"Schema file not found: {self.schema_file_path}")
            
            with open(self.schema_file_path, 'r', encoding='utf-8') as file:
                schema_sql = file.read()
            
            # Split into individual statements
            statements = self._split_sql_statements(schema_sql)
            
            connection = pyodbc.connect(self.config.connection_string)
            cursor = connection.cursor()
            
            try:
                for statement in statements:
                    if statement.strip():
                        self.logger.debug(f"Executing: {statement[:100]}...")
                        cursor.execute(statement)
                
                connection.commit()
                self.logger.info("Database schema created successfully")
                
            except Exception as e:
                connection.rollback()
                raise DatabaseError(f"Schema creation failed: {str(e)}")
            finally:
                connection.close()
                
        except Exception as e:
            self.logger.error(f"Failed to create schema: {str(e)}")
            raise
    
    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """Split SQL content into individual statements."""
        # Remove comments and split by GO statements
        lines = sql_content.split('\n')
        statements = []
        current_statement = []
        
        for line in lines:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('--') or line.startswith('/*'):
                continue
            
            # Check for GO statement (SQL Server batch separator)
            if line.upper() == 'GO':
                if current_statement:
                    statements.append('\n'.join(current_statement))
                    current_statement = []
            else:
                current_statement.append(line)
        
        # Add final statement if exists
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        return statements
    
    async def _verify_schema(self) -> bool:
        """Verify that the schema was created correctly."""
        try:
            connection = pyodbc.connect(self.config.connection_string)
            cursor = connection.cursor()
            
            # Check tables
            required_tables = [
                'news_sources', 'keywords', 'news_articles', 'article_keywords',
                'sentiment_analyses', 'sentiment_analysis_articles', 
                'execution_logs', 'configuration'
            ]
            
            for table in required_tables:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = '{table}'
                """)
                
                if cursor.fetchone()[0] == 0:
                    self.logger.error(f"Table '{table}' not found")
                    return False
            
            # Check views
            required_views = ['vw_articles_with_source', 'vw_sentiment_analyses_summary']
            
            for view in required_views:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS 
                    WHERE TABLE_NAME = '{view}'
                """)
                
                if cursor.fetchone()[0] == 0:
                    self.logger.warning(f"View '{view}' not found")
            
            # Check stored procedures
            required_procedures = ['sp_GetOrCreateNewsSource', 'sp_GetOrCreateKeyword', 'sp_DeduplicateArticles']
            
            for proc in required_procedures:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES 
                    WHERE ROUTINE_NAME = '{proc}' AND ROUTINE_TYPE = 'PROCEDURE'
                """)
                
                if cursor.fetchone()[0] == 0:
                    self.logger.warning(f"Stored procedure '{proc}' not found")
            
            connection.close()
            self.logger.info("Schema verification completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Schema verification failed: {str(e)}")
            return False
    
    async def migrate_data_from_excel(self, excel_files: List[str]) -> Dict[str, int]:
        """
        Migrate data from Excel files to SQL Server database.
        
        Args:
            excel_files: List of Excel file paths to migrate
            
        Returns:
            Dictionary with migration statistics
        """
        migration_stats = {
            'articles_migrated': 0,
            'sentiment_analyses_migrated': 0,
            'errors': 0,
            'files_processed': 0
        }
        
        try:
            # Create database handler for migration
            db_handler = DatabaseHandler(self.config)
            
            for excel_file in excel_files:
                try:
                    self.logger.info(f"Processing Excel file: {excel_file}")
                    
                    # Process based on file type
                    if 'news' in excel_file.lower() or 'scrapping' in excel_file.lower():
                        articles = await self._extract_articles_from_excel(excel_file)
                        if articles:
                            await db_handler.save_articles(articles)
                            migration_stats['articles_migrated'] += len(articles)
                    
                    elif 'sentiment' in excel_file.lower():
                        analyses = await self._extract_sentiment_from_excel(excel_file)
                        if analyses:
                            for analysis in analyses:
                                await db_handler.save_sentiment_analysis(analysis)
                            migration_stats['sentiment_analyses_migrated'] += len(analyses)
                    
                    migration_stats['files_processed'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing file {excel_file}: {str(e)}")
                    migration_stats['errors'] += 1
            
            self.logger.info(f"Data migration completed: {migration_stats}")
            return migration_stats
            
        except Exception as e:
            self.logger.error(f"Data migration failed: {str(e)}")
            migration_stats['errors'] += 1
            return migration_stats
    
    async def _extract_articles_from_excel(self, excel_file: str) -> List[NewsArticle]:
        """Extract news articles from Excel file."""
        try:
            import pandas as pd
            
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            articles = []
            for _, row in df.iterrows():
                try:
                    # Map Excel columns to NewsArticle fields
                    # Adjust column names based on actual Excel structure
                    article = NewsArticle(
                        title=str(row.get('title', row.get('Title', ''))),
                        content=str(row.get('content', row.get('Content', ''))),
                        url=str(row.get('url', row.get('URL', ''))),
                        source=str(row.get('source', row.get('Source', 'Unknown'))),
                        published_date=pd.to_datetime(row.get('published_date', row.get('Date', datetime.utcnow()))),
                        scraped_date=pd.to_datetime(row.get('scraped_date', datetime.utcnow())),
                        language=str(row.get('language', 'en')),
                        author=str(row.get('author', row.get('Author', ''))),
                        category=str(row.get('category', row.get('Category', ''))),
                        keywords=str(row.get('keywords', '')).split(',') if row.get('keywords') else []
                    )
                    
                    # Validate article
                    if article.title and article.content and article.url:
                        articles.append(article)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing article row: {str(e)}")
                    continue
            
            self.logger.info(f"Extracted {len(articles)} articles from {excel_file}")
            return articles
            
        except Exception as e:
            self.logger.error(f"Failed to extract articles from {excel_file}: {str(e)}")
            return []
    
    async def _extract_sentiment_from_excel(self, excel_file: str) -> List[SentimentAnalysis]:
        """Extract sentiment analyses from Excel file."""
        try:
            import pandas as pd
            from .models import SentimentLabel
            
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            analyses = []
            for _, row in df.iterrows():
                try:
                    # Map Excel columns to SentimentAnalysis fields
                    analysis = SentimentAnalysis(
                        sentiment_score=float(row.get('sentiment_score', 0.0)),
                        sentiment_label=SentimentLabel(row.get('sentiment_label', 'neutral')),
                        confidence=float(row.get('confidence', 0.0)),
                        summary=str(row.get('summary', '')),
                        analysis_date=pd.to_datetime(row.get('analysis_date', datetime.utcnow())),
                        model_version=str(row.get('model_version', 'legacy')),
                        role_context=str(row.get('role_context', '')),
                        article_ids=[]  # Will need to be mapped separately
                    )
                    
                    # Validate analysis
                    if analysis.summary:
                        analyses.append(analysis)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing sentiment row: {str(e)}")
                    continue
            
            self.logger.info(f"Extracted {len(analyses)} sentiment analyses from {excel_file}")
            return analyses
            
        except Exception as e:
            self.logger.error(f"Failed to extract sentiment analyses from {excel_file}: {str(e)}")
            return []
    
    async def backup_database(self, backup_path: str) -> bool:
        """
        Create a backup of the database.
        
        Args:
            backup_path: Path where backup should be stored
            
        Returns:
            True if backup successful, False otherwise
        """
        try:
            connection = pyodbc.connect(self.config.connection_string)
            cursor = connection.cursor()
            
            # Get database name from connection string
            db_name = self._extract_database_name()
            
            backup_query = f"""
            BACKUP DATABASE [{db_name}] 
            TO DISK = '{backup_path}'
            WITH FORMAT, INIT, COMPRESSION
            """
            
            cursor.execute(backup_query)
            connection.close()
            
            self.logger.info(f"Database backup created successfully: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Database backup failed: {str(e)}")
            return False
    
    def _extract_database_name(self) -> str:
        """Extract database name from connection string."""
        # Parse connection string to get database name
        parts = self.config.connection_string.split(';')
        for part in parts:
            if 'database=' in part.lower() or 'initial catalog=' in part.lower():
                return part.split('=')[1].strip()
        return 'NewsScrapingDB'  # Default name
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """
        Get the current migration status and database statistics.
        
        Returns:
            Dictionary with migration status information
        """
        try:
            db_handler = DatabaseHandler(self.config)
            
            # Get table counts
            stats = {}
            
            tables = ['news_articles', 'news_sources', 'sentiment_analyses', 'keywords', 'execution_logs']
            
            for table in tables:
                result = await db_handler.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                stats[f"{table}_count"] = result[0]['count'] if result else 0
            
            # Get latest records
            latest_article = await db_handler.execute_query(
                "SELECT TOP 1 scraped_date FROM news_articles ORDER BY scraped_date DESC"
            )
            
            latest_sentiment = await db_handler.execute_query(
                "SELECT TOP 1 analysis_date FROM sentiment_analyses ORDER BY analysis_date DESC"
            )
            
            stats['latest_article_date'] = latest_article[0]['scraped_date'] if latest_article else None
            stats['latest_sentiment_date'] = latest_sentiment[0]['analysis_date'] if latest_sentiment else None
            stats['schema_version'] = '1.0.0'
            stats['migration_complete'] = await self._verify_schema()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get migration status: {str(e)}")
            return {'error': str(e)}


# Utility functions for database operations
async def initialize_database_from_config(config: DatabaseConfig) -> bool:
    """
    Initialize database using configuration.
    
    Args:
        config: Database configuration
        
    Returns:
        True if initialization successful
    """
    migration = DatabaseMigration(config)
    return await migration.initialize_database()


async def migrate_excel_data(config: DatabaseConfig, excel_directory: str) -> Dict[str, int]:
    """
    Migrate all Excel files from a directory.
    
    Args:
        config: Database configuration
        excel_directory: Directory containing Excel files
        
    Returns:
        Migration statistics
    """
    migration = DatabaseMigration(config)
    
    # Find all Excel files in directory
    excel_files = []
    if os.path.exists(excel_directory):
        for file in os.listdir(excel_directory):
            if file.endswith(('.xlsx', '.xls')):
                excel_files.append(os.path.join(excel_directory, file))
    
    return await migration.migrate_data_from_excel(excel_files)