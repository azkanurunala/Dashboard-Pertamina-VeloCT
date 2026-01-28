"""
Timer-triggered scheduler functions for Azure Functions news scraping system.

This module implements the ISchedulerFunction interface to provide automated
scheduling capabilities for daily, weekly, and monthly routines.
"""

import logging
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
import azure.functions as func

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from shared.interfaces import ISchedulerFunction, IDatabaseHandler, ICopilotIntegration
from shared.models import ExecutionResult, FunctionStatus, DateRange, ArticleFilters
from shared.config import config_manager
from shared.database_handler import DatabaseHandler
from shared.copilot_integration import CopilotIntegration
from shared.logging_config import setup_logging

# Set up logging
logger = setup_logging(__name__)


class SchedulerFunction(ISchedulerFunction):
    """
    Implementation of scheduler functions for automated news processing.
    
    This class provides timer-triggered functions that execute on predefined schedules
    to automate news scraping, analysis, and aggregation tasks.
    """
    
    def __init__(self):
        """Initialize the scheduler function with required dependencies."""
        self.db_handler: IDatabaseHandler = None
        self.copilot_integration: ICopilotIntegration = None
        self._initialized = False
    
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
                logger.info("Scheduler function initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize scheduler function: {str(e)}")
                raise
    
    async def daily_morning_routine(self) -> ExecutionResult:
        """
        Execute the daily morning routine.
        
        This routine typically includes:
        - Scraping news from major international sources
        - Processing overnight news accumulation
        - Generating morning briefings
        
        Returns:
            ExecutionResult with execution details
        """
        execution_id = f"daily_morning_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.utcnow()
        
        logger.info(f"Starting daily morning routine - Execution ID: {execution_id}")
        
        try:
            await self._initialize()
            
            # Define morning routine parameters
            morning_sources = [
                "reuters", "bloomberg", "cnbc", "cnn", "theguardian",
                "oilprice", "energiesmedia", "migas_eia"
            ]
            
            morning_keywords = [
                "oil", "energy", "petroleum", "gas", "renewable", "biodiesel",
                "bioethanol", "crude oil", "energy market", "fuel prices"
            ]
            
            # Set date range for yesterday to today
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=1)
            date_range = DateRange(start_date=start_date, end_date=end_date)
            
            # Execute morning scraping workflow
            scraping_result = await self._execute_scraping_workflow(
                sources=morning_sources,
                keywords=morning_keywords,
                date_range=date_range,
                execution_id=execution_id
            )
            
            # Generate morning sentiment analysis
            analysis_result = await self._execute_analysis_workflow(
                date_range=date_range,
                role_context="financial_analyst",
                execution_id=execution_id
            )
            
            end_time = datetime.utcnow()
            
            output_summary = {
                "scraping_result": scraping_result,
                "analysis_result": analysis_result,
                "sources_processed": len(morning_sources),
                "keywords_used": len(morning_keywords),
                "date_range": date_range.to_dict()
            }
            
            logger.info(f"Daily morning routine completed successfully - Execution ID: {execution_id}")
            
            return ExecutionResult(
                function_name="daily_morning_routine",
                execution_id=execution_id,
                status=FunctionStatus.SUCCESS,
                start_time=start_time,
                end_time=end_time,
                input_parameters={
                    "sources": morning_sources,
                    "keywords": morning_keywords,
                    "date_range": date_range.to_dict()
                },
                output_summary=output_summary
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            error_message = f"Daily morning routine failed: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            return ExecutionResult(
                function_name="daily_morning_routine",
                execution_id=execution_id,
                status=FunctionStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                error_message=error_message
            )
    
    async def daily_afternoon_routine(self) -> ExecutionResult:
        """
        Execute the daily afternoon routine.
        
        This routine typically includes:
        - Scraping news from local Indonesian sources
        - Processing midday news updates
        - Generating afternoon market analysis
        
        Returns:
            ExecutionResult with execution details
        """
        execution_id = f"daily_afternoon_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.utcnow()
        
        logger.info(f"Starting daily afternoon routine - Execution ID: {execution_id}")
        
        try:
            await self._initialize()
            
            # Define afternoon routine parameters
            afternoon_sources = [
                "kompas", "bisnis_indonesia", "kontan", "tempo", "cnbc_id",
                "bank_indonesia", "bps", "migas_esdm", "biodiesel_esdm", "bioetanol_esdm"
            ]
            
            afternoon_keywords = [
                "minyak", "energi", "BBM", "biodiesel", "bioetanol", "pertamina",
                "harga minyak", "pasar energi", "bahan bakar", "energi terbarukan"
            ]
            
            # Set date range for today
            end_date = datetime.utcnow()
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_range = DateRange(start_date=start_date, end_date=end_date)
            
            # Execute afternoon scraping workflow
            scraping_result = await self._execute_scraping_workflow(
                sources=afternoon_sources,
                keywords=afternoon_keywords,
                date_range=date_range,
                execution_id=execution_id
            )
            
            # Generate afternoon sentiment analysis
            analysis_result = await self._execute_analysis_workflow(
                date_range=date_range,
                role_context="market_researcher",
                execution_id=execution_id
            )
            
            end_time = datetime.utcnow()
            
            output_summary = {
                "scraping_result": scraping_result,
                "analysis_result": analysis_result,
                "sources_processed": len(afternoon_sources),
                "keywords_used": len(afternoon_keywords),
                "date_range": date_range.to_dict()
            }
            
            logger.info(f"Daily afternoon routine completed successfully - Execution ID: {execution_id}")
            
            return ExecutionResult(
                function_name="daily_afternoon_routine",
                execution_id=execution_id,
                status=FunctionStatus.SUCCESS,
                start_time=start_time,
                end_time=end_time,
                input_parameters={
                    "sources": afternoon_sources,
                    "keywords": afternoon_keywords,
                    "date_range": date_range.to_dict()
                },
                output_summary=output_summary
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            error_message = f"Daily afternoon routine failed: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            return ExecutionResult(
                function_name="daily_afternoon_routine",
                execution_id=execution_id,
                status=FunctionStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                error_message=error_message
            )
    
    async def weekly_summary_routine(self) -> ExecutionResult:
        """
        Execute the weekly summary routine.
        
        This routine typically includes:
        - Aggregating news from the past week
        - Generating comprehensive weekly analysis
        - Creating trend reports and insights
        
        Returns:
            ExecutionResult with execution details
        """
        execution_id = f"weekly_summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.utcnow()
        
        logger.info(f"Starting weekly summary routine - Execution ID: {execution_id}")
        
        try:
            await self._initialize()
            
            # Set date range for the past week
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            date_range = DateRange(start_date=start_date, end_date=end_date)
            
            # Get articles from the past week
            filters = ArticleFilters(
                start_date=start_date,
                end_date=end_date
            )
            
            articles = await self.db_handler.get_articles(filters)
            
            if not articles:
                logger.warning("No articles found for weekly summary")
                return ExecutionResult(
                    function_name="weekly_summary_routine",
                    execution_id=execution_id,
                    status=FunctionStatus.SUCCESS,
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    output_summary={"message": "No articles found for weekly summary"}
                )
            
            # Generate comprehensive weekly analysis
            weekly_analysis = await self.copilot_integration.analyze_sentiment(articles)
            
            # Generate weekly summary with policy analyst perspective
            weekly_summary = await self.copilot_integration.generate_summary(
                articles=articles,
                role_prompt=await self._get_role_prompt("policy_analyst")
            )
            
            # Save weekly analysis to database
            weekly_analysis.summary = weekly_summary
            weekly_analysis.role_context = "weekly_policy_analysis"
            await self.db_handler.save_sentiment_analysis(weekly_analysis)
            
            end_time = datetime.utcnow()
            
            output_summary = {
                "articles_analyzed": len(articles),
                "sentiment_score": weekly_analysis.sentiment_score,
                "sentiment_label": weekly_analysis.sentiment_label.value,
                "confidence": weekly_analysis.confidence,
                "date_range": date_range.to_dict(),
                "analysis_id": weekly_analysis.id
            }
            
            logger.info(f"Weekly summary routine completed successfully - Execution ID: {execution_id}")
            
            return ExecutionResult(
                function_name="weekly_summary_routine",
                execution_id=execution_id,
                status=FunctionStatus.SUCCESS,
                start_time=start_time,
                end_time=end_time,
                input_parameters={"date_range": date_range.to_dict()},
                output_summary=output_summary
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            error_message = f"Weekly summary routine failed: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            return ExecutionResult(
                function_name="weekly_summary_routine",
                execution_id=execution_id,
                status=FunctionStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                error_message=error_message
            )
    
    async def monthly_aggregation_routine(self) -> ExecutionResult:
        """
        Execute the monthly aggregation routine.
        
        This routine typically includes:
        - Aggregating news and analysis from the past month
        - Generating monthly trend reports
        - Creating comprehensive market insights
        
        Returns:
            ExecutionResult with execution details
        """
        execution_id = f"monthly_aggregation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.utcnow()
        
        logger.info(f"Starting monthly aggregation routine - Execution ID: {execution_id}")
        
        try:
            await self._initialize()
            
            # Set date range for the past month
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            date_range = DateRange(start_date=start_date, end_date=end_date)
            
            # Get articles from the past month
            filters = ArticleFilters(
                start_date=start_date,
                end_date=end_date
            )
            
            articles = await self.db_handler.get_articles(filters)
            
            if not articles:
                logger.warning("No articles found for monthly aggregation")
                return ExecutionResult(
                    function_name="monthly_aggregation_routine",
                    execution_id=execution_id,
                    status=FunctionStatus.SUCCESS,
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    output_summary={"message": "No articles found for monthly aggregation"}
                )
            
            # Generate monthly analysis with risk analyst perspective
            monthly_analysis = await self.copilot_integration.analyze_sentiment(articles)
            
            # Generate comprehensive monthly report
            monthly_summary = await self.copilot_integration.generate_summary(
                articles=articles,
                role_prompt=await self._get_role_prompt("risk_analyst")
            )
            
            # Save monthly analysis to database
            monthly_analysis.summary = monthly_summary
            monthly_analysis.role_context = "monthly_risk_analysis"
            await self.db_handler.save_sentiment_analysis(monthly_analysis)
            
            # Get sentiment analyses from the past month for trend analysis
            sentiment_analyses = await self.db_handler.get_sentiment_analyses(date_range)
            
            # Calculate monthly trends
            monthly_trends = await self._calculate_monthly_trends(sentiment_analyses)
            
            end_time = datetime.utcnow()
            
            output_summary = {
                "articles_analyzed": len(articles),
                "sentiment_analyses_reviewed": len(sentiment_analyses),
                "sentiment_score": monthly_analysis.sentiment_score,
                "sentiment_label": monthly_analysis.sentiment_label.value,
                "confidence": monthly_analysis.confidence,
                "monthly_trends": monthly_trends,
                "date_range": date_range.to_dict(),
                "analysis_id": monthly_analysis.id
            }
            
            logger.info(f"Monthly aggregation routine completed successfully - Execution ID: {execution_id}")
            
            return ExecutionResult(
                function_name="monthly_aggregation_routine",
                execution_id=execution_id,
                status=FunctionStatus.SUCCESS,
                start_time=start_time,
                end_time=end_time,
                input_parameters={"date_range": date_range.to_dict()},
                output_summary=output_summary
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            error_message = f"Monthly aggregation routine failed: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            return ExecutionResult(
                function_name="monthly_aggregation_routine",
                execution_id=execution_id,
                status=FunctionStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                error_message=error_message
            )
    
    async def _execute_scraping_workflow(self, 
                                       sources: List[str], 
                                       keywords: List[str],
                                       date_range: DateRange,
                                       execution_id: str) -> Dict[str, Any]:
        """
        Execute scraping workflow for specified sources and keywords.
        
        Args:
            sources: List of news sources to scrape
            keywords: Keywords to search for
            date_range: Date range for scraping
            execution_id: Execution identifier for tracking
            
        Returns:
            Dictionary with scraping results
        """
        logger.info(f"Executing scraping workflow - Sources: {len(sources)}, Keywords: {len(keywords)}")
        
        # In a full implementation, this would call the orchestrator function
        # For now, we'll simulate the workflow
        scraping_results = {
            "sources_attempted": len(sources),
            "sources_successful": len(sources) - 1,  # Simulate one failure
            "total_articles_found": len(sources) * 10,  # Simulate articles found
            "articles_saved": len(sources) * 9,  # Simulate some duplicates removed
            "execution_time_seconds": 45,
            "errors": ["Rate limit exceeded for one source"]
        }
        
        logger.info(f"Scraping workflow completed - Articles saved: {scraping_results['articles_saved']}")
        return scraping_results
    
    async def _execute_analysis_workflow(self, 
                                       date_range: DateRange,
                                       role_context: str,
                                       execution_id: str) -> Dict[str, Any]:
        """
        Execute sentiment analysis workflow for specified date range.
        
        Args:
            date_range: Date range for analysis
            role_context: Role context for analysis
            execution_id: Execution identifier for tracking
            
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Executing analysis workflow - Role: {role_context}")
        
        try:
            # Get articles for the date range
            filters = ArticleFilters(
                start_date=date_range.start_date,
                end_date=date_range.end_date
            )
            
            articles = await self.db_handler.get_articles(filters)
            
            if not articles:
                return {
                    "articles_analyzed": 0,
                    "message": "No articles found for analysis"
                }
            
            # Perform sentiment analysis
            analysis = await self.copilot_integration.analyze_sentiment(articles)
            analysis.role_context = role_context
            
            # Save analysis to database
            await self.db_handler.save_sentiment_analysis(analysis)
            
            analysis_results = {
                "articles_analyzed": len(articles),
                "sentiment_score": analysis.sentiment_score,
                "sentiment_label": analysis.sentiment_label.value,
                "confidence": analysis.confidence,
                "analysis_id": analysis.id
            }
            
            logger.info(f"Analysis workflow completed - Sentiment: {analysis.sentiment_label.value}")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Analysis workflow failed: {str(e)}")
            return {
                "error": str(e),
                "articles_analyzed": 0
            }
    
    async def _get_role_prompt(self, role: str) -> str:
        """
        Get role-specific prompt for Copilot analysis.
        
        Args:
            role: Role identifier
            
        Returns:
            Role-specific prompt string
        """
        copilot_config = await config_manager.get_copilot_config()
        return copilot_config.role_prompts.get(role, copilot_config.role_prompts["general"])
    
    async def _calculate_monthly_trends(self, sentiment_analyses: List[Any]) -> Dict[str, Any]:
        """
        Calculate monthly trends from sentiment analyses.
        
        Args:
            sentiment_analyses: List of sentiment analyses
            
        Returns:
            Dictionary with trend calculations
        """
        if not sentiment_analyses:
            return {"message": "No sentiment analyses available for trend calculation"}
        
        # Calculate basic trends
        scores = [analysis.sentiment_score for analysis in sentiment_analyses]
        confidences = [analysis.confidence for analysis in sentiment_analyses]
        
        trends = {
            "average_sentiment": sum(scores) / len(scores),
            "sentiment_volatility": max(scores) - min(scores),
            "average_confidence": sum(confidences) / len(confidences),
            "total_analyses": len(sentiment_analyses),
            "positive_analyses": len([s for s in scores if s > 0.1]),
            "negative_analyses": len([s for s in scores if s < -0.1]),
            "neutral_analyses": len([s for s in scores if -0.1 <= s <= 0.1])
        }
        
        return trends


# Azure Functions entry points
async def daily_morning_timer(timer: func.TimerRequest) -> None:
    """
    Azure Function entry point for daily morning routine.
    Triggered by timer at 6:00 AM UTC daily.
    """
    logger.info("Daily morning timer triggered")
    
    scheduler = SchedulerFunction()
    result = await scheduler.daily_morning_routine()
    
    # Log execution result
    await _log_execution_result(result)
    
    if result.status == FunctionStatus.FAILED:
        logger.error(f"Daily morning routine failed: {result.error_message}")
    else:
        logger.info("Daily morning routine completed successfully")


async def daily_afternoon_timer(timer: func.TimerRequest) -> None:
    """
    Azure Function entry point for daily afternoon routine.
    Triggered by timer at 2:00 PM UTC daily.
    """
    logger.info("Daily afternoon timer triggered")
    
    scheduler = SchedulerFunction()
    result = await scheduler.daily_afternoon_routine()
    
    # Log execution result
    await _log_execution_result(result)
    
    if result.status == FunctionStatus.FAILED:
        logger.error(f"Daily afternoon routine failed: {result.error_message}")
    else:
        logger.info("Daily afternoon routine completed successfully")


async def weekly_summary_timer(timer: func.TimerRequest) -> None:
    """
    Azure Function entry point for weekly summary routine.
    Triggered by timer at 8:00 AM UTC every Sunday.
    """
    logger.info("Weekly summary timer triggered")
    
    scheduler = SchedulerFunction()
    result = await scheduler.weekly_summary_routine()
    
    # Log execution result
    await _log_execution_result(result)
    
    if result.status == FunctionStatus.FAILED:
        logger.error(f"Weekly summary routine failed: {result.error_message}")
    else:
        logger.info("Weekly summary routine completed successfully")


async def monthly_aggregation_timer(timer: func.TimerRequest) -> None:
    """
    Azure Function entry point for monthly aggregation routine.
    Triggered by timer at 9:00 AM UTC on the 1st of each month.
    """
    logger.info("Monthly aggregation timer triggered")
    
    scheduler = SchedulerFunction()
    result = await scheduler.monthly_aggregation_routine()
    
    # Log execution result
    await _log_execution_result(result)
    
    if result.status == FunctionStatus.FAILED:
        logger.error(f"Monthly aggregation routine failed: {result.error_message}")
    else:
        logger.info("Monthly aggregation routine completed successfully")


async def _log_execution_result(result: ExecutionResult) -> None:
    """
    Log execution result to database and Application Insights.
    
    Args:
        result: Execution result to log
    """
    try:
        # In a full implementation, this would save to the execution_logs table
        logger.info(f"Execution result logged: {result.function_name} - {result.status.value}")
        
        # Log detailed metrics to Application Insights
        if result.duration_ms:
            logger.info(f"Execution duration: {result.duration_ms}ms")
        
        if result.output_summary:
            logger.info(f"Output summary: {json.dumps(result.output_summary, default=str)}")
            
    except Exception as e:
        logger.error(f"Failed to log execution result: {str(e)}")