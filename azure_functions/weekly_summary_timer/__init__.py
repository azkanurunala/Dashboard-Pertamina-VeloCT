"""
Weekly Summary Timer Function
Triggers at scheduled time to execute weekly summary routine
"""
import azure.functions as func
from orchestration.scheduler_function import weekly_summary_timer

async def main(timer: func.TimerRequest) -> None:
    """Azure Function entry point for weekly summary timer."""
    await weekly_summary_timer(timer)
