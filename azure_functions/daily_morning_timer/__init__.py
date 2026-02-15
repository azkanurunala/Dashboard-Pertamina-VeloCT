"""
Daily Morning Timer Function
Triggers at scheduled time to execute morning scraping routine
"""
import azure.functions as func
from orchestration.scheduler_function import daily_morning_timer as main

# Export the main function
__all__ = ['main']
