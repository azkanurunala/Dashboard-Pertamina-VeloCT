"""
Daily Afternoon Timer Function
Triggers at scheduled time to execute afternoon scraping routine
"""
import azure.functions as func
from orchestration.scheduler_function import daily_afternoon_timer

async def main(timer: func.TimerRequest) -> None:
    """Azure Function entry point for daily afternoon timer."""
    await daily_afternoon_timer(timer)
