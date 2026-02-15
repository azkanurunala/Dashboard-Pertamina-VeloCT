"""
Weekly Summary Timer Function
Triggers at scheduled time to execute weekly summary routine
"""
import azure.functions as func
from orchestration.scheduler_function import weekly_summary_timer as main

# Export the main function
__all__ = ['main']
