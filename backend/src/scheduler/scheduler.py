"""APScheduler configuration for the Macro Reasoning Agent.

Runs the daily reasoning job on a schedule.
"""
import os
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from .daily_job import run_daily_job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def job_listener(event):
    """Listener for job events."""
    if event.exception:
        logger.error(f"Job crashed: {event.exception}")
    else:
        logger.info(f"Job executed successfully at {event.scheduled_run_time}")


class ReasoningScheduler:
    """Scheduler for running daily reasoning updates."""
    
    def __init__(self, db_path: str = "sqlite:///macro_reasoning.db"):
        self.db_path = db_path
        self.scheduler: Optional[AsyncIOScheduler] = None
    
    def start(self, hour: int = 9, minute: int = 0):
        """
        Start the scheduler.
        
        Args:
            hour: Hour to run (0-23), default 9 AM
            minute: Minute to run (0-59), default 0
        """
        self.scheduler = AsyncIOScheduler()
        
        # Add job listener
        self.scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        # Schedule daily job
        self.scheduler.add_job(
            self._run_job,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="daily_reasoning",
            name="Daily Reasoning Update",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info(f"Scheduler started. Daily job scheduled for {hour:02d}:{minute:02d}")
    
    async def _run_job(self):
        """Run the daily job."""
        logger.info("Running scheduled daily job...")
        try:
            results = await run_daily_job(self.db_path)
            logger.info(f"Daily job completed: {results['successful']}/{results['questions_processed']} successful")
        except Exception as e:
            logger.error(f"Daily job failed: {e}")
    
    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("Scheduler shutdown")
    
    def get_jobs(self):
        """Get list of scheduled jobs."""
        if self.scheduler:
            return self.scheduler.get_jobs()
        return []


def run_scheduler():
    """Run the scheduler (blocks forever)."""
    import asyncio
    
    scheduler = ReasoningScheduler()
    scheduler.start(hour=9, minute=0)  # Run at 9:00 AM daily
    
    print("Scheduler is running. Press Ctrl+C to exit.")
    print("Daily job scheduled for 09:00 UTC")
    
    try:
        # Keep the event loop running
        loop = asyncio.get_event_loop()
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("\nScheduler stopped.")


if __name__ == "__main__":
    run_scheduler()
