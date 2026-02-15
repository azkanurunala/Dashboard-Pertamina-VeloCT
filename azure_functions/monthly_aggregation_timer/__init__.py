"""
Monthly Aggregation Timer Function
Triggers at scheduled time to execute monthly aggregation routine
"""
import azure.functions as func
from orchestration.scheduler_function import monthly_aggregation_timer as main

# Export the main function
__all__ = ['main']
