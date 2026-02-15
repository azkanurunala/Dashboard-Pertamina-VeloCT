"""
Daily Afternoon Timer Function
Triggers at scheduled time to execute afternoon scraping routine
"""
import azure.functions as func
from orchestration.scheduler_function import daily_afternoon_timer as main

# Export the main function
__all__ = ['main']
