"""
Excel to SQL Server data migration utilities.
Handles reading Excel files and migrating data to the new database schema.
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import uuid
import re

try:
    import pandas as pd
    PandasSeries = pd.Series
except ImportError:
    pd = None
    PandasSeries = Any

from .models import (
    NewsArticle, SentimentAnalysis, SentimentLabel, DatabaseConfig
)
from .database_handler import DatabaseHandler
from .interfaces import DatabaseError, ProcessingError
from .logging_config import get_logger


class ExcelDataMigrator:
    """
    Handles migration of data from Excel files to SQL Server database.
    Supports various Excel formats and provides data transformation capabilities.
    """
    
    def __init__(self, db_config: DatabaseConfig):
        """
        Initialize the Excel data migrator.
        
        Args:
            db_config: Database configuration for target SQL Server
        """
        self.db_config = db_config
        self.logger = get_logger(__name__)
        self.db_handler: Optional[DatabaseHandler] = None
        
        # Column mapping configurations for different Excel formats
        self.column_mappings = {
            'news_articles': {
                'title': ['title', 'Title', 'TITLE', 'headline', 'Headline'],
                'content': ['content', 'Content', 'CONTENT', 'body', 'Body', 'text', 'Text'],
                'url': ['url', 'URL', 'link', 'Link', 'web_link', 'website'],
                'source': ['source', 'Source', 'SOURCE', 'publisher', 'Publisher', 'site'],
                'published_date': ['published_date', 'date', 'Date', 'DATE', 'publish_date', 'publication_date'],
                'scraped_date': ['scraped_date', 'scrape_date', 'collected_date', 'extraction_date'],
                'language': ['language', 'Language', 'lang', 'Lang'],
                'author': ['author', 'Author', 'AUTHOR', 'writer', 'Writer'],
                'category': ['category', 'Category', 'CATEGORY', 'section', 'Section'],
                'keywords': ['keywords', 'Keywords', 'KEYWORDS', 'tags', 'Tags']
            },
            'sentiment_analysis': {
                'sentiment_score': ['sentiment_score', 'score', 'Score', 'sentiment_value'],
                'sentiment_label': ['sentiment_label', 'sentiment', 'Sentiment', 'label', 'Label'],
                'confidence': ['confidence', 'Confidence', 'certainty', 'probability'],
                'summary': ['summary', 'Summary', 'SUMMARY', 'analysis', 'Analysis'],
                'analysis_date': ['analysis_date', 'date', 'Date', 'processed_date'],
                'model_version': ['model_version', 'model', 'Model', 'version'],
                'role_context': ['role_context', 'role', 'Role', 'context', 'analyst_type']
            }
        }
    
    async def initialize(self) -> None:
        """Initialize database connection."""
        if not self.db_handler:
            self.db_handler = DatabaseHandler(self.db_config)
            
            # Verify database connection
            if not await self.db_handler.health_check():
                raise DatabaseError("Failed to connect to target database")
    
    async def migrate_excel_files(self, excel_directory: str) -> Dict[str, Any]:
        """
        Migrate all Excel files from a directory to SQL Server.
        
        Args:
            excel_directory: Directory containing Excel files to migrate
            
        Returns:
            Migration statistics and results
        """
        if pd is None:
            raise ProcessingError("pandas library is required for Excel migration")
        
        await self.initialize()
        
        migration_stats = {
            'files_processed': 0,
            'files_failed': 0,
            'articles_migrated': 0,
            'sentiment_analyses_migrated': 0,
            'errors': [],
            'processing_time': 0,
            'start_time': datetime.utcnow()
        }
        
        try:
            # Find all Excel files
            excel_files = self._find_excel_files(excel_directory)
            
            if not excel_files:
                self.logger.warning(f"No Excel files found in directory: {excel_directory}")
                return migration_stats
            
            self.logger.info(f"Found {len(excel_files)} Excel files to process")
            
            # Process each Excel file
            for excel_file in excel_files:
                try:
                    self.logger.info(f"Processing file: {excel_file}")
                    file_stats = await self._process_excel_file(excel_file)
                    
                    migration_stats['files_processed'] += 1
                    migration_stats['articles_migrated'] += file_stats.get('articles', 0)
                    migration_stats['sentiment_analyses_migrated'] += file_stats.get('sentiment_analyses', 0)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process file {excel_file}: {str(e)}")
                    migration_stats['files_failed'] += 1
                    migration_stats['errors'].append({
                        'file': excel_file,
                        'error': str(e),
                        'timestamp': datetime.utcnow().isoformat()
                    })
            
            # Calculate processing time
            end_time = datetime.utcnow()
            migration_stats['processing_time'] = (end_time - migration_stats['start_time']).total_seconds()
            migration_stats['end_time'] = end_time
            
            self.logger.info(f"Migration completed: {migration_stats}")
            return migration_stats
            
        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            migration_stats['errors'].append({
                'error': f"Migration process failed: {str(e)}",
                'timestamp': datetime.utcnow().isoformat()
            })
            raise ProcessingError(f"Excel migration failed: {str(e)}")
    
    def _find_excel_files(self, directory: str) -> List[str]:
        """Find all Excel files in the specified directory."""
        excel_files = []
        
        if not os.path.exists(directory):
            self.logger.warning(f"Directory does not exist: {directory}")
            return excel_files
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.xlsx', '.xls')):
                    excel_files.append(os.path.join(root, file))
        
        return excel_files
    
    async def _process_excel_file(self, excel_file: str) -> Dict[str, int]:
        """
        Process a single Excel file and migrate its data.
        
        Args:
            excel_file: Path to the Excel file
            
        Returns:
            Statistics for this file processing
        """
        file_stats = {'articles': 0, 'sentiment_analyses': 0}
        
        try:
            # Determine file type based on filename and content
            file_type = self._determine_file_type(excel_file)
            
            if file_type == 'news_articles':
                articles = await self._extract_articles_from_excel(excel_file)
                if articles:
                    await self.db_handler.save_articles(articles)
                    file_stats['articles'] = len(articles)
                    self.logger.info(f"Migrated {len(articles)} articles from {excel_file}")
            
            elif file_type == 'sentiment_analysis':
                analyses = await self._extract_sentiment_from_excel(excel_file)
                if analyses:
                    for analysis in analyses:
                        await self.db_handler.save_sentiment_analysis(analysis)
                    file_stats['sentiment_analyses'] = len(analyses)
                    self.logger.info(f"Migrated {len(analyses)} sentiment analyses from {excel_file}")
            
            else:
                self.logger.warning(f"Unknown file type for {excel_file}, attempting generic processing")
                # Try both types
                try:
                    articles = await self._extract_articles_from_excel(excel_file)
                    if articles:
                        await self.db_handler.save_articles(articles)
                        file_stats['articles'] = len(articles)
                except Exception:
                    analyses = await self._extract_sentiment_from_excel(excel_file)
                    if analyses:
                        for analysis in analyses:
                            await self.db_handler.save_sentiment_analysis(analysis)
                        file_stats['sentiment_analyses'] = len(analyses)
            
            return file_stats
            
        except Exception as e:
            self.logger.error(f"Error processing Excel file {excel_file}: {str(e)}")
            raise ProcessingError(f"Failed to process {excel_file}: {str(e)}")
    
    def _determine_file_type(self, excel_file: str) -> str:
        """
        Determine the type of data in the Excel file based on filename.
        
        Args:
            excel_file: Path to the Excel file
            
        Returns:
            File type ('news_articles', 'sentiment_analysis', or 'unknown')
        """
        filename = os.path.basename(excel_file).lower()
        
        # Check for news/scraping indicators
        news_indicators = ['news', 'scrapping', 'scraping', 'articles', 'berita']
        if any(indicator in filename for indicator in news_indicators):
            return 'news_articles'
        
        # Check for sentiment analysis indicators
        sentiment_indicators = ['sentiment', 'analysis', 'analisis', 'mood']
        if any(indicator in filename for indicator in sentiment_indicators):
            return 'sentiment_analysis'
        
        return 'unknown'
    
    async def _extract_articles_from_excel(self, excel_file: str) -> List[NewsArticle]:
        """
        Extract news articles from Excel file.
        
        Args:
            excel_file: Path to the Excel file
            
        Returns:
            List of NewsArticle objects
        """
        try:
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            if df.empty:
                self.logger.warning(f"Excel file {excel_file} is empty")
                return []
            
            # Map columns to standard names
            column_mapping = self._map_columns(df.columns, 'news_articles')
            
            articles = []
            for index, row in df.iterrows():
                try:
                    # Extract and validate article data
                    article_data = self._extract_article_data(row, column_mapping)
                    
                    if self._validate_article_data(article_data):
                        article = NewsArticle(**article_data)
                        articles.append(article)
                    else:
                        self.logger.warning(f"Invalid article data at row {index + 1} in {excel_file}")
                
                except Exception as e:
                    self.logger.warning(f"Error processing row {index + 1} in {excel_file}: {str(e)}")
                    continue
            
            self.logger.info(f"Extracted {len(articles)} valid articles from {excel_file}")
            return articles
            
        except Exception as e:
            self.logger.error(f"Failed to extract articles from {excel_file}: {str(e)}")
            return []
    
    async def _extract_sentiment_from_excel(self, excel_file: str) -> List[SentimentAnalysis]:
        """
        Extract sentiment analyses from Excel file.
        
        Args:
            excel_file: Path to the Excel file
            
        Returns:
            List of SentimentAnalysis objects
        """
        try:
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            if df.empty:
                self.logger.warning(f"Excel file {excel_file} is empty")
                return []
            
            # Map columns to standard names
            column_mapping = self._map_columns(df.columns, 'sentiment_analysis')
            
            analyses = []
            for index, row in df.iterrows():
                try:
                    # Extract and validate sentiment data
                    sentiment_data = self._extract_sentiment_data(row, column_mapping)
                    
                    if self._validate_sentiment_data(sentiment_data):
                        analysis = SentimentAnalysis(**sentiment_data)
                        analyses.append(analysis)
                    else:
                        self.logger.warning(f"Invalid sentiment data at row {index + 1} in {excel_file}")
                
                except Exception as e:
                    self.logger.warning(f"Error processing row {index + 1} in {excel_file}: {str(e)}")
                    continue
            
            self.logger.info(f"Extracted {len(analyses)} valid sentiment analyses from {excel_file}")
            return analyses
            
        except Exception as e:
            self.logger.error(f"Failed to extract sentiment analyses from {excel_file}: {str(e)}")
            return []
    
    def _map_columns(self, excel_columns: List[str], data_type: str) -> Dict[str, str]:
        """
        Map Excel columns to standard field names.
        
        Args:
            excel_columns: List of column names from Excel file
            data_type: Type of data ('news_articles' or 'sentiment_analysis')
            
        Returns:
            Dictionary mapping standard field names to Excel column names
        """
        mapping = {}
        mappings_config = self.column_mappings.get(data_type, {})
        
        for standard_field, possible_names in mappings_config.items():
            for excel_col in excel_columns:
                if excel_col in possible_names:
                    mapping[standard_field] = excel_col
                    break
        
        return mapping
    
    def _extract_article_data(self, row: PandasSeries, column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Extract article data from Excel row using column mapping."""
        article_data = {
            'id': str(uuid.uuid4()),
            'title': self._get_mapped_value(row, column_mapping, 'title', ''),
            'content': self._get_mapped_value(row, column_mapping, 'content', ''),
            'url': self._get_mapped_value(row, column_mapping, 'url', ''),
            'source': self._get_mapped_value(row, column_mapping, 'source', 'Unknown'),
            'published_date': self._parse_date(self._get_mapped_value(row, column_mapping, 'published_date')),
            'scraped_date': self._parse_date(self._get_mapped_value(row, column_mapping, 'scraped_date')) or datetime.utcnow(),
            'language': self._get_mapped_value(row, column_mapping, 'language', 'en'),
            'author': self._get_mapped_value(row, column_mapping, 'author'),
            'category': self._get_mapped_value(row, column_mapping, 'category'),
            'keywords': self._parse_keywords(self._get_mapped_value(row, column_mapping, 'keywords', ''))
        }
        
        return article_data
    
    def _extract_sentiment_data(self, row: PandasSeries, column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Extract sentiment analysis data from Excel row using column mapping."""
        sentiment_data = {
            'id': str(uuid.uuid4()),
            'sentiment_score': float(self._get_mapped_value(row, column_mapping, 'sentiment_score', 0.0)),
            'sentiment_label': self._parse_sentiment_label(self._get_mapped_value(row, column_mapping, 'sentiment_label', 'neutral')),
            'confidence': float(self._get_mapped_value(row, column_mapping, 'confidence', 0.0)),
            'summary': self._get_mapped_value(row, column_mapping, 'summary', ''),
            'analysis_date': self._parse_date(self._get_mapped_value(row, column_mapping, 'analysis_date')) or datetime.utcnow(),
            'model_version': self._get_mapped_value(row, column_mapping, 'model_version', 'legacy'),
            'role_context': self._get_mapped_value(row, column_mapping, 'role_context'),
            'article_ids': []  # Will need to be linked separately
        }
        
        return sentiment_data
    
    def _get_mapped_value(self, row: PandasSeries, column_mapping: Dict[str, str], 
                         field: str, default: Any = None) -> Any:
        """Get value from Excel row using column mapping."""
        excel_column = column_mapping.get(field)
        if excel_column and excel_column in row.index:
            value = row[excel_column]
            # Handle NaN values
            if pd and pd.isna(value):
                return default
            elif value is None or (isinstance(value, float) and str(value).lower() == 'nan'):
                return default
            return str(value).strip() if isinstance(value, str) else value
        return default
    
    def _parse_date(self, date_value: Any) -> Optional[datetime]:
        """Parse date value from various formats."""
        if not date_value or (pd and pd.isna(date_value)):
            return None
        
        if date_value is None or (isinstance(date_value, float) and str(date_value).lower() == 'nan'):
            return None
        
        if isinstance(date_value, datetime):
            return date_value
        
        if isinstance(date_value, str):
            # Try various date formats
            date_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d/%m/%Y',
                '%m/%d/%Y',
                '%d-%m-%Y',
                '%Y/%m/%d'
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_value.strip(), fmt)
                except ValueError:
                    continue
        
        # Try pandas to_datetime as fallback
        if pd:
            try:
                return pd.to_datetime(date_value)
            except Exception:
                return None
        
        return None
    
    def _parse_keywords(self, keywords_value: Any) -> List[str]:
        """Parse keywords from various formats."""
        if not keywords_value or (pd and pd.isna(keywords_value)):
            return []
        
        if keywords_value is None or (isinstance(keywords_value, float) and str(keywords_value).lower() == 'nan'):
            return []
        
        keywords_str = str(keywords_value).strip()
        if not keywords_str:
            return []
        
        # Split by common delimiters
        delimiters = [',', ';', '|', '\n']
        keywords = [keywords_str]
        
        for delimiter in delimiters:
            new_keywords = []
            for keyword in keywords:
                new_keywords.extend([k.strip() for k in keyword.split(delimiter)])
            keywords = new_keywords
        
        # Filter out empty keywords
        return [k for k in keywords if k]
    
    def _parse_sentiment_label(self, label_value: Any) -> SentimentLabel:
        """Parse sentiment label from various formats."""
        if not label_value or (pd and pd.isna(label_value)):
            return SentimentLabel.NEUTRAL
        
        if label_value is None or (isinstance(label_value, float) and str(label_value).lower() == 'nan'):
            return SentimentLabel.NEUTRAL
        
        label_str = str(label_value).lower().strip()
        
        if label_str in ['positive', 'pos', '1', 'good', 'bullish']:
            return SentimentLabel.POSITIVE
        elif label_str in ['negative', 'neg', '-1', 'bad', 'bearish']:
            return SentimentLabel.NEGATIVE
        else:
            return SentimentLabel.NEUTRAL
    
    def _validate_article_data(self, article_data: Dict[str, Any]) -> bool:
        """Validate that article data has required fields."""
        required_fields = ['title', 'content', 'url', 'source']
        
        for field in required_fields:
            value = article_data.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                return False
        
        # Validate URL format
        url = article_data.get('url', '')
        if not (url.startswith('http://') or url.startswith('https://') or '://' in url):
            return False
        
        return True
    
    def _validate_sentiment_data(self, sentiment_data: Dict[str, Any]) -> bool:
        """Validate that sentiment data has required fields."""
        required_fields = ['summary']
        
        for field in required_fields:
            value = sentiment_data.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                return False
        
        # Validate score ranges
        score = sentiment_data.get('sentiment_score', 0.0)
        if not -1.0 <= score <= 1.0:
            return False
        
        confidence = sentiment_data.get('confidence', 0.0)
        if not 0.0 <= confidence <= 1.0:
            return False
        
        return True
    
    async def create_migration_report(self, migration_stats: Dict[str, Any], 
                                   output_file: Optional[str] = None) -> str:
        """
        Create a detailed migration report.
        
        Args:
            migration_stats: Migration statistics from migrate_excel_files
            output_file: Optional file path to save the report
            
        Returns:
            Report content as string
        """
        report_lines = [
            "Excel to SQL Server Migration Report",
            "=" * 50,
            f"Migration Date: {migration_stats.get('start_time', datetime.utcnow()).strftime('%Y-%m-%d %H:%M:%S')}",
            f"Processing Time: {migration_stats.get('processing_time', 0):.2f} seconds",
            "",
            "Summary:",
            f"  Files Processed: {migration_stats.get('files_processed', 0)}",
            f"  Files Failed: {migration_stats.get('files_failed', 0)}",
            f"  Articles Migrated: {migration_stats.get('articles_migrated', 0)}",
            f"  Sentiment Analyses Migrated: {migration_stats.get('sentiment_analyses_migrated', 0)}",
            ""
        ]
        
        # Add error details if any
        errors = migration_stats.get('errors', [])
        if errors:
            report_lines.extend([
                "Errors:",
                "-" * 20
            ])
            for error in errors:
                report_lines.append(f"  {error.get('timestamp', '')}: {error.get('error', '')}")
                if 'file' in error:
                    report_lines.append(f"    File: {error['file']}")
            report_lines.append("")
        
        # Add database statistics
        if self.db_handler:
            try:
                db_stats = await self._get_database_statistics()
                report_lines.extend([
                    "Database Statistics:",
                    "-" * 20,
                    f"  Total Articles: {db_stats.get('total_articles', 0)}",
                    f"  Total Sources: {db_stats.get('total_sources', 0)}",
                    f"  Total Keywords: {db_stats.get('total_keywords', 0)}",
                    f"  Total Sentiment Analyses: {db_stats.get('total_sentiment_analyses', 0)}",
                    ""
                ])
            except Exception as e:
                report_lines.append(f"  Error getting database statistics: {str(e)}")
        
        report_content = "\n".join(report_lines)
        
        # Save to file if requested
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                self.logger.info(f"Migration report saved to: {output_file}")
            except Exception as e:
                self.logger.error(f"Failed to save migration report: {str(e)}")
        
        return report_content
    
    async def _get_database_statistics(self) -> Dict[str, int]:
        """Get current database statistics."""
        stats = {}
        
        try:
            # Get article count
            result = await self.db_handler.execute_query("SELECT COUNT(*) as count FROM news_articles")
            stats['total_articles'] = result[0]['count'] if result else 0
            
            # Get source count
            result = await self.db_handler.execute_query("SELECT COUNT(*) as count FROM news_sources")
            stats['total_sources'] = result[0]['count'] if result else 0
            
            # Get keyword count
            result = await self.db_handler.execute_query("SELECT COUNT(*) as count FROM keywords")
            stats['total_keywords'] = result[0]['count'] if result else 0
            
            # Get sentiment analysis count
            result = await self.db_handler.execute_query("SELECT COUNT(*) as count FROM sentiment_analyses")
            stats['total_sentiment_analyses'] = result[0]['count'] if result else 0
            
        except Exception as e:
            self.logger.error(f"Error getting database statistics: {str(e)}")
        
        return stats
    
    async def close(self) -> None:
        """Close database connections and cleanup resources."""
        if self.db_handler:
            await self.db_handler.close()
            self.db_handler = None


# Utility functions for Excel migration
async def migrate_excel_directory(db_config: DatabaseConfig, 
                                excel_directory: str,
                                report_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Migrate all Excel files from a directory to SQL Server.
    
    Args:
        db_config: Database configuration
        excel_directory: Directory containing Excel files
        report_file: Optional path to save migration report
        
    Returns:
        Migration statistics
    """
    migrator = ExcelDataMigrator(db_config)
    
    try:
        # Perform migration
        stats = await migrator.migrate_excel_files(excel_directory)
        
        # Generate report if requested
        if report_file:
            await migrator.create_migration_report(stats, report_file)
        
        return stats
        
    finally:
        await migrator.close()


async def migrate_single_excel_file(db_config: DatabaseConfig, 
                                  excel_file: str) -> Dict[str, Any]:
    """
    Migrate a single Excel file to SQL Server.
    
    Args:
        db_config: Database configuration
        excel_file: Path to Excel file
        
    Returns:
        Migration statistics
    """
    migrator = ExcelDataMigrator(db_config)
    
    try:
        await migrator.initialize()
        
        # Process single file
        file_stats = await migrator._process_excel_file(excel_file)
        
        return {
            'files_processed': 1,
            'files_failed': 0,
            'articles_migrated': file_stats.get('articles', 0),
            'sentiment_analyses_migrated': file_stats.get('sentiment_analyses', 0),
            'errors': []
        }
        
    finally:
        await migrator.close()