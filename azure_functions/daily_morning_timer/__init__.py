"""
Daily Morning Timer Function
Triggers at scheduled time to execute morning scraping routine
"""
import azure.functions as func
from orchestration.scheduler_function import daily_morning_timer

async def main(timer: func.TimerRequest) -> None:
    """Azure Function entry point for daily morning timer."""
    await daily_morning_timer(timer)
