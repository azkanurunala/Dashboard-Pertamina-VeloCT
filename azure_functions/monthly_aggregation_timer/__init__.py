"""
Monthly Aggregation Timer Function
Triggers at scheduled time to execute monthly aggregation routine
"""
import azure.functions as func
from orchestration.scheduler_function import monthly_aggregation_timer

async def main(timer: func.TimerRequest) -> None:
    """Azure Function entry point for monthly aggregation timer."""
    await monthly_aggregation_timer(timer)
