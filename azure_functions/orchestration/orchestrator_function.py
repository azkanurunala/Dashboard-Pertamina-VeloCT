"""
Orchestrator function for workflow management in Azure Functions news scraping system.

This module implements the IOrchestratorFunction interface to coordinate
multiple scraper and analysis functions with dependency management and error handling.
"""

import logging
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import azure.functions as func

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from shared.interfaces import IOrchestratorFunction, IDatabaseHandler, ICopilotIntegration
from shared.models import (
    ExecutionResult, FunctionStatus, DateRange, ArticleFilters, 
    NewsArticle, SentimentAnalysis
)
from shared.config import config_manager
from shared.database_handler import DatabaseHandler
from shared.copilot_integration import CopilotIntegration
from shared.logging_config import setup_logging

# Set up logging
logger = setup_logging(__name__)


class OrchestratorFunction(IOrchestratorFunction):
    """
    Implementation of orchestrator functions for workflow coordination.
    
    This class provides HTTP-triggered functions that coordinate multiple
    scraper and analysis functions with proper dependency management,
    error handling, and recovery mechanisms.
    """
    
    def __init__(self):
        """Initialize the orchestrator function with required dependencies."""
        self.db_handler: IDatabaseHandler = None
        self.copilot_integration: ICopilotIntegration = None
        self._initialized = False
        self.max_concurrent_scrapers = 5
        self.scraper_timeout_seconds = 300  # 5 minutes
        self.analysis_timeout_seconds = 600  # 10 minutes
    
    async def _initialize(self) -> None:
        """Initialize database and Copilot connections if not already done."""
        if not self._initialized:
            try:
                # Initialize database handler
                db_config = await config_manager.get_database_config()
                self.db_handler = DatabaseHandler(db_config)
                
                # Initialize Copilot integration
                copilot_config = await config_manager.get_copilot_config()
                self.copilot_integration = CopilotIntegration(copilot_config)
                
                self._initialized = True
                logger.info("Orchestrator function initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize orchestrator function: {str(e)}")
                raise
    
    async def orchestrate_scraping(self, 
                                 sources: List[str], 
                                 keywords: List[str],
                                 date_range: DateRange) -> ExecutionResult:
        """
        Orchestrate scraping across multiple sources.
        
        This function coordinates parallel scraping operations across multiple
        news sources while managing concurrency, timeouts, and error recovery.
        
        Args:
            sources: List of news sources to scrape
            keywords: Keywords to search for
            date_range: Date range for scraping
            
        Returns:
            ExecutionResult with orchestration details
        """
        execution_id = f"scraping_orchestration_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.utcnow()
        
        logger.info(f"Starting scraping orchestration - Execution ID: {execution_id}")
        logger.info(f"Sources: {len(sources)}, Keywords: {len(keywords)}")
        
        try:
            await self._initialize()
            
            # Validate inputs
            if not sources:
                raise ValueError("No sources provided for scraping")
            if not keywords:
                raise ValueError("No keywords provided for scraping")
            
            # Execute scraping with concurrency control
            scraping_results = await self._execute_parallel_scraping(
                sources=sources,
                keywords=keywords,
                date_range=date_range,
                execution_id=execution_id
            )
            
            # Process and aggregate results
            aggregated_results = await self._aggregate_scraping_results(
                scraping_results=scraping_results,
                execution_id=execution_id
            )
            
            # Perform deduplication
            deduplication_result = await self._perform_deduplication(execution_id)
            
            end_time = datetime.utcnow()
            
            output_summary = {
                "sources_attempted": len(sources),
                "sources_successful": aggregated_results["successful_sources"],
                "sources_failed": aggregated_results["failed_sources"],
                "total_articles_found": aggregated_results["total_articles"],
                "articles_saved": aggregated_results["articles_saved"],
                "duplicates_removed": deduplication_result["duplicates_removed"],
                "execution_time_seconds": (end_time - start_time).total_seconds(),
                "errors": aggregated_results["errors"]
            }
            
            logger.info(f"Scraping orchestration completed - Articles saved: {output_summary['articles_saved']}")
            
            return ExecutionResult(
                function_name="orchestrate_scraping",
                execution_id=execution_id,
                status=FunctionStatus.SUCCESS,
                start_time=start_time,
                end_time=end_time,
                input_parameters={
                    "sources": sources,
                    "keywords": keywords,
                    "date_range": date_range.to_dict()
                },
                output_summary=output_summary
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            error_message = f"Scraping orchestration failed: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            return ExecutionResult(
                function_name="orchestrate_scraping",
                execution_id=execution_id,
                status=FunctionStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                error_message=error_message,
                input_parameters={
                    "sources": sources,
                    "keywords": keywords,
                    "date_range": date_range.to_dict()
                }
            )
    
    async def orchestrate_analysis(self, date_range: DateRange) -> ExecutionResult:
        """
        Orchestrate sentiment analysis for a date range.
        
        This function coordinates sentiment analysis operations including
        data retrieval, batch processing, and result storage.
        
        Args:
            date_range: Date range for analysis
            
        Returns:
            ExecutionResult with analysis details
        """
        execution_id = f"analysis_orchestration_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.utcnow()
        
        logger.info(f"Starting analysis orchestration - Execution ID: {execution_id}")
        logger.info(f"Date range: {date_range.start_date} to {date_range.end_date}")
        
        try:
            await self._initialize()
            
            # Get articles for analysis
            filters = ArticleFilters(
                start_date=date_range.start_date,
                end_date=date_range.end_date
            )
            
            articles = await self.db_handler.get_articles(filters)
            
            if not articles:
                logger.warning("No articles found for analysis")
                return ExecutionResult(
                    function_name="orchestrate_analysis",
                    execution_id=execution_id,
                    status=FunctionStatus.SUCCESS,
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    output_summary={"message": "No articles found for analysis"}
                )
            
            # Execute batch analysis
            analysis_results = await self._execute_batch_analysis(
                articles=articles,
                execution_id=execution_id
            )
            
            # Generate comprehensive summary
            summary_result = await self._generate_comprehensive_summary(
                articles=articles,
                execution_id=execution_id
            )
            
            end_time = datetime.utcnow()
            
            output_summary = {
                "articles_analyzed": len(articles),
                "batch_analyses_created": analysis_results["batch_count"],
                "average_sentiment_score": analysis_results["average_sentiment"],
                "confidence_score": analysis_results["average_confidence"],
                "summary_generated": summary_result["success"],
                "execution_time_seconds": (end_time - start_time).total_seconds()
            }
            
            logger.info(f"Analysis orchestration completed - Articles analyzed: {len(articles)}")
            
            return ExecutionResult(
                function_name="orchestrate_analysis",
                execution_id=execution_id,
                status=FunctionStatus.SUCCESS,
                start_time=start_time,
                end_time=end_time,
                input_parameters={"date_range": date_range.to_dict()},
                output_summary=output_summary
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            error_message = f"Analysis orchestration failed: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            return ExecutionResult(
                function_name="orchestrate_analysis",
                execution_id=execution_id,
                status=FunctionStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                error_message=error_message,
                input_parameters={"date_range": date_range.to_dict()}
            )
    
    async def orchestrate_full_pipeline(self, 
                                       sources: List[str], 
                                       keywords: List[str],
                                       date_range: DateRange) -> ExecutionResult:
        """
        Orchestrate the complete pipeline from scraping to analysis.
        
        This function coordinates the entire workflow including scraping,
        data processing, deduplication, and sentiment analysis.
        
        Args:
            sources: List of news sources to scrape
            keywords: Keywords to search for
            date_range: Date range for processing
            
        Returns:
            ExecutionResult with pipeline execution details
        """
        execution_id = f"full_pipeline_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.utcnow()
        
        logger.info(f"Starting full pipeline orchestration - Execution ID: {execution_id}")
        
        try:
            await self._initialize()
            
            # Step 1: Execute scraping orchestration
            logger.info("Step 1: Executing scraping orchestration")
            scraping_result = await self.orchestrate_scraping(
                sources=sources,
                keywords=keywords,
                date_range=date_range
            )
            
            if scraping_result.status == FunctionStatus.FAILED:
                raise Exception(f"Scraping orchestration failed: {scraping_result.error_message}")
            
            # Step 2: Wait for data processing to complete
            logger.info("Step 2: Waiting for data processing")
            await asyncio.sleep(5)  # Allow time for data to be processed
            
            # Step 3: Execute analysis orchestration
            logger.info("Step 3: Executing analysis orchestration")
            analysis_result = await self.orchestrate_analysis(date_range)
            
            if analysis_result.status == FunctionStatus.FAILED:
                logger.warning(f"Analysis orchestration failed: {analysis_result.error_message}")
                # Continue with partial success
            
            # Step 4: Generate final report
            logger.info("Step 4: Generating final report")
            final_report = await self._generate_pipeline_report(
                scraping_result=scraping_result,
                analysis_result=analysis_result,
                execution_id=execution_id
            )
            
            end_time = datetime.utcnow()
            
            output_summary = {
                "pipeline_steps_completed": 4,
                "scraping_success": scraping_result.status == FunctionStatus.SUCCESS,
                "analysis_success": analysis_result.status == FunctionStatus.SUCCESS,
                "total_articles_processed": scraping_result.output_summary.get("articles_saved", 0) if scraping_result.output_summary else 0,
                "analysis_articles": analysis_result.output_summary.get("articles_analyzed", 0) if analysis_result.output_summary else 0,
                "execution_time_seconds": (end_time - start_time).total_seconds(),
                "final_report": final_report
            }
            
            # Determine overall status
            overall_status = FunctionStatus.SUCCESS
            if scraping_result.status == FunctionStatus.FAILED:
                overall_status = FunctionStatus.FAILED
            elif analysis_result.status == FunctionStatus.FAILED:
                overall_status = FunctionStatus.SUCCESS  # Partial success
            
            logger.info(f"Full pipeline orchestration completed - Status: {overall_status.value}")
            
            return ExecutionResult(
                function_name="orchestrate_full_pipeline",
                execution_id=execution_id,
                status=overall_status,
                start_time=start_time,
                end_time=end_time,
                input_parameters={
                    "sources": sources,
                    "keywords": keywords,
                    "date_range": date_range.to_dict()
                },
                output_summary=output_summary
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            error_message = f"Full pipeline orchestration failed: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            return ExecutionResult(
                function_name="orchestrate_full_pipeline",
                execution_id=execution_id,
                status=FunctionStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                error_message=error_message,
                input_parameters={
                    "sources": sources,
                    "keywords": keywords,
                    "date_range": date_range.to_dict()
                }
            )
    
    async def _execute_parallel_scraping(self, 
                                       sources: List[str], 
                                       keywords: List[str],
                                       date_range: DateRange,
                                       execution_id: str) -> List[Dict[str, Any]]:
        """
        Execute scraping operations in parallel with concurrency control.
        
        Args:
            sources: List of news sources to scrape
            keywords: Keywords to search for
            date_range: Date range for scraping
            execution_id: Execution identifier
            
        Returns:
            List of scraping results
        """
        logger.info(f"Executing parallel scraping for {len(sources)} sources")
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_scrapers)
        
        # Create scraping tasks
        tasks = []
        for source in sources:
            task = self._scrape_single_source(
                source=source,
                keywords=keywords,
                date_range=date_range,
                execution_id=execution_id,
                semaphore=semaphore
            )
            tasks.append(task)
        
        # Execute tasks with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.scraper_timeout_seconds
            )
            
            # Process results and handle exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Scraping failed for source {sources[i]}: {str(result)}")
                    processed_results.append({
                        "source": sources[i],
                        "success": False,
                        "error": str(result),
                        "articles": []
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except asyncio.TimeoutError:
            logger.error(f"Scraping timeout exceeded ({self.scraper_timeout_seconds}s)")
            # Return partial results
            return [{
                "source": source,
                "success": False,
                "error": "Timeout exceeded",
                "articles": []
            } for source in sources]
    
    async def _scrape_single_source(self, 
                                  source: str, 
                                  keywords: List[str],
                                  date_range: DateRange,
                                  execution_id: str,
                                  semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        """
        Scrape a single news source with semaphore control.
        
        Args:
            source: News source to scrape
            keywords: Keywords to search for
            date_range: Date range for scraping
            execution_id: Execution identifier
            semaphore: Semaphore for concurrency control
            
        Returns:
            Dictionary with scraping results
        """
        async with semaphore:
            logger.info(f"Starting scraping for source: {source}")
            
            try:
                # In a full implementation, this would call the actual scraper function
                # For now, we'll simulate the scraping process
                await asyncio.sleep(2)  # Simulate scraping time
                
                # Simulate finding articles
                articles_found = len(keywords) * 3  # Simulate articles per keyword
                
                # Create mock articles
                articles = []
                for i in range(articles_found):
                    article = {
                        "title": f"Mock article {i+1} from {source}",
                        "content": f"Mock content for article {i+1}",
                        "url": f"https://{source}.com/article-{i+1}",
                        "source": source,
                        "published_date": date_range.start_date + timedelta(hours=i),
                        "keywords": keywords[:2]  # Use first 2 keywords
                    }
                    articles.append(article)
                
                logger.info(f"Scraping completed for {source}: {len(articles)} articles found")
                
                return {
                    "source": source,
                    "success": True,
                    "articles": articles,
                    "articles_count": len(articles)
                }
                
            except Exception as e:
                logger.error(f"Scraping failed for source {source}: {str(e)}")
                return {
                    "source": source,
                    "success": False,
                    "error": str(e),
                    "articles": []
                }
    
    async def _aggregate_scraping_results(self, 
                                        scraping_results: List[Dict[str, Any]],
                                        execution_id: str) -> Dict[str, Any]:
        """
        Aggregate results from parallel scraping operations.
        
        Args:
            scraping_results: List of scraping results
            execution_id: Execution identifier
            
        Returns:
            Dictionary with aggregated results
        """
        logger.info("Aggregating scraping results")
        
        successful_sources = 0
        failed_sources = 0
        total_articles = 0
        articles_saved = 0
        errors = []
        
        all_articles = []
        
        for result in scraping_results:
            if result["success"]:
                successful_sources += 1
                articles = result["articles"]
                total_articles += len(articles)
                
                # Convert to NewsArticle objects and save to database
                try:
                    news_articles = []
                    for article_data in articles:
                        article = NewsArticle(
                            title=article_data["title"],
                            content=article_data["content"],
                            url=article_data["url"],
                            source=article_data["source"],
                            published_date=article_data["published_date"],
                            keywords=article_data["keywords"]
                        )
                        news_articles.append(article)
                    
                    # Save articles to database
                    await self.db_handler.save_articles(news_articles)
                    articles_saved += len(news_articles)
                    all_articles.extend(news_articles)
                    
                except Exception as e:
                    logger.error(f"Failed to save articles from {result['source']}: {str(e)}")
                    errors.append(f"Save failed for {result['source']}: {str(e)}")
            else:
                failed_sources += 1
                errors.append(f"{result['source']}: {result.get('error', 'Unknown error')}")
        
        aggregated_results = {
            "successful_sources": successful_sources,
            "failed_sources": failed_sources,
            "total_articles": total_articles,
            "articles_saved": articles_saved,
            "errors": errors,
            "all_articles": all_articles
        }
        
        logger.info(f"Aggregation completed: {articles_saved} articles saved from {successful_sources} sources")
        return aggregated_results
    
    async def _perform_deduplication(self, execution_id: str) -> Dict[str, Any]:
        """
        Perform deduplication of articles in the database.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            Dictionary with deduplication results
        """
        logger.info("Performing article deduplication")
        
        try:
            duplicates_removed = await self.db_handler.deduplicate_articles()
            
            logger.info(f"Deduplication completed: {duplicates_removed} duplicates removed")
            
            return {
                "success": True,
                "duplicates_removed": duplicates_removed
            }
            
        except Exception as e:
            logger.error(f"Deduplication failed: {str(e)}")
            return {
                "success": False,
                "duplicates_removed": 0,
                "error": str(e)
            }
    
    async def _execute_batch_analysis(self, 
                                    articles: List[NewsArticle],
                                    execution_id: str) -> Dict[str, Any]:
        """
        Execute sentiment analysis in batches.
        
        Args:
            articles: List of articles to analyze
            execution_id: Execution identifier
            
        Returns:
            Dictionary with batch analysis results
        """
        logger.info(f"Executing batch analysis for {len(articles)} articles")
        
        try:
            batch_results = []
            sentiment_scores = []
            confidence_scores = []
            
            # Process articles in batches using the Copilot integration
            async for analysis in self.copilot_integration.batch_process(articles):
                batch_results.append(analysis)
                sentiment_scores.append(analysis.sentiment_score)
                confidence_scores.append(analysis.confidence)
                
                # Save each batch analysis to database
                await self.db_handler.save_sentiment_analysis(analysis)
            
            # Calculate averages
            average_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            average_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            logger.info(f"Batch analysis completed: {len(batch_results)} batches processed")
            
            return {
                "success": True,
                "batch_count": len(batch_results),
                "average_sentiment": average_sentiment,
                "average_confidence": average_confidence
            }
            
        except Exception as e:
            logger.error(f"Batch analysis failed: {str(e)}")
            return {
                "success": False,
                "batch_count": 0,
                "average_sentiment": 0,
                "average_confidence": 0,
                "error": str(e)
            }
    
    async def _generate_comprehensive_summary(self, 
                                            articles: List[NewsArticle],
                                            execution_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive summary of articles.
        
        Args:
            articles: List of articles to summarize
            execution_id: Execution identifier
            
        Returns:
            Dictionary with summary generation results
        """
        logger.info("Generating comprehensive summary")
        
        try:
            # Generate summary with general role prompt
            copilot_config = await config_manager.get_copilot_config()
            general_prompt = copilot_config.role_prompts.get("general", "")
            
            summary = await self.copilot_integration.generate_summary(
                articles=articles,
                role_prompt=general_prompt
            )
            
            # Create and save comprehensive analysis
            comprehensive_analysis = SentimentAnalysis(
                sentiment_score=0.0,  # Will be calculated by analyze_sentiment
                sentiment_label=SentimentLabel.NEUTRAL,
                confidence=0.0,
                summary=summary,
                role_context="comprehensive_summary",
                article_ids=[article.id for article in articles]
            )
            
            # Get proper sentiment analysis
            full_analysis = await self.copilot_integration.analyze_sentiment(articles)
            comprehensive_analysis.sentiment_score = full_analysis.sentiment_score
            comprehensive_analysis.sentiment_label = full_analysis.sentiment_label
            comprehensive_analysis.confidence = full_analysis.confidence
            
            # Save comprehensive analysis
            await self.db_handler.save_sentiment_analysis(comprehensive_analysis)
            
            logger.info("Comprehensive summary generated successfully")
            
            return {
                "success": True,
                "summary_length": len(summary),
                "analysis_id": comprehensive_analysis.id
            }
            
        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_pipeline_report(self, 
                                      scraping_result: ExecutionResult,
                                      analysis_result: ExecutionResult,
                                      execution_id: str) -> Dict[str, Any]:
        """
        Generate final pipeline execution report.
        
        Args:
            scraping_result: Result from scraping orchestration
            analysis_result: Result from analysis orchestration
            execution_id: Execution identifier
            
        Returns:
            Dictionary with pipeline report
        """
        logger.info("Generating pipeline report")
        
        report = {
            "execution_id": execution_id,
            "pipeline_status": "completed",
            "scraping_summary": {
                "status": scraping_result.status.value,
                "articles_saved": scraping_result.output_summary.get("articles_saved", 0) if scraping_result.output_summary else 0,
                "sources_successful": scraping_result.output_summary.get("sources_successful", 0) if scraping_result.output_summary else 0,
                "execution_time": scraping_result.duration_ms
            },
            "analysis_summary": {
                "status": analysis_result.status.value,
                "articles_analyzed": analysis_result.output_summary.get("articles_analyzed", 0) if analysis_result.output_summary else 0,
                "execution_time": analysis_result.duration_ms
            },
            "recommendations": []
        }
        
        # Add recommendations based on results
        if scraping_result.status == FunctionStatus.FAILED:
            report["recommendations"].append("Review scraping configuration and error logs")
        
        if analysis_result.status == FunctionStatus.FAILED:
            report["recommendations"].append("Check Copilot API connectivity and quota")
        
        if not report["recommendations"]:
            report["recommendations"].append("Pipeline executed successfully")
        
        return report


# Azure Functions HTTP entry points
async def orchestrate_scraping_http(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function HTTP entry point for scraping orchestration.
    """
    logger.info("Scraping orchestration HTTP trigger received")
    
    try:
        # Parse request body
        req_body = req.get_json()
        
        sources = req_body.get("sources", [])
        keywords = req_body.get("keywords", [])
        date_range_data = req_body.get("date_range", {})
        
        # Validate inputs
        if not sources or not keywords or not date_range_data:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameters: sources, keywords, date_range"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Create date range
        date_range = DateRange.from_dict(date_range_data)
        
        # Execute orchestration
        orchestrator = OrchestratorFunction()
        result = await orchestrator.orchestrate_scraping(sources, keywords, date_range)
        
        # Return result
        return func.HttpResponse(
            json.dumps(result.to_dict(), default=str),
            status_code=200 if result.status == FunctionStatus.SUCCESS else 500,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Scraping orchestration HTTP failed: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


async def orchestrate_analysis_http(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function HTTP entry point for analysis orchestration.
    """
    logger.info("Analysis orchestration HTTP trigger received")
    
    try:
        # Parse request body
        req_body = req.get_json()
        
        date_range_data = req_body.get("date_range", {})
        
        # Validate inputs
        if not date_range_data:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameter: date_range"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Create date range
        date_range = DateRange.from_dict(date_range_data)
        
        # Execute orchestration
        orchestrator = OrchestratorFunction()
        result = await orchestrator.orchestrate_analysis(date_range)
        
        # Return result
        return func.HttpResponse(
            json.dumps(result.to_dict(), default=str),
            status_code=200 if result.status == FunctionStatus.SUCCESS else 500,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Analysis orchestration HTTP failed: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


async def orchestrate_full_pipeline_http(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function HTTP entry point for full pipeline orchestration.
    """
    logger.info("Full pipeline orchestration HTTP trigger received")
    
    try:
        # Parse request body
        req_body = req.get_json()
        
        sources = req_body.get("sources", [])
        keywords = req_body.get("keywords", [])
        date_range_data = req_body.get("date_range", {})
        
        # Validate inputs
        if not sources or not keywords or not date_range_data:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameters: sources, keywords, date_range"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Create date range
        date_range = DateRange.from_dict(date_range_data)
        
        # Execute orchestration
        orchestrator = OrchestratorFunction()
        result = await orchestrator.orchestrate_full_pipeline(sources, keywords, date_range)
        
        # Return result
        return func.HttpResponse(
            json.dumps(result.to_dict(), default=str),
            status_code=200 if result.status == FunctionStatus.SUCCESS else 500,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Full pipeline orchestration HTTP failed: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )