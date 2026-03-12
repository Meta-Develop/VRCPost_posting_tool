"""Scheduler engine.

Uses APScheduler to manage job execution schedules.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from loguru import logger

from src.config.settings import AppSettings
from src.scheduler.jobs import JobStatus, RepeatType, ScheduledJob


class SchedulerEngine:
    """Scheduler engine.

    Manages job registration, execution, and persistence.
    """

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self._scheduler = BackgroundScheduler(timezone=settings.scheduler.timezone)
        self._jobs: dict[str, ScheduledJob] = {}
        self._job_callback: Optional[Callable] = None
        self._jobs_file = Path(settings.scheduler.jobs_file)

    def set_callback(self, callback: Callable) -> None:
        """Set the callback invoked when a job runs.

        Args:
            callback: Function that receives a job and executes it.
        """
        self._job_callback = callback

    def start(self) -> None:
        """Start the scheduler."""
        self._load_jobs()
        self._scheduler.start()
        logger.info(f"Scheduler started ({len(self._jobs)} jobs)")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._save_jobs()
        if self._scheduler.running:
            self._scheduler.shutdown()
        logger.info("Scheduler stopped")

    def add_job(self, job: ScheduledJob) -> str:
        """Add a job.

        Args:
            job: The job to add.

        Returns:
            Job ID.
        """
        self._jobs[job.id] = job

        # Register with APScheduler
        if job.repeat_type == RepeatType.NONE:
            trigger = DateTrigger(run_date=job.scheduled_at)
        elif job.repeat_type == RepeatType.DAILY:
            trigger = CronTrigger(
                hour=job.scheduled_at.hour,
                minute=job.scheduled_at.minute,
            )
        elif job.repeat_type == RepeatType.WEEKLY:
            trigger = CronTrigger(
                day_of_week=job.scheduled_at.strftime("%a").lower(),
                hour=job.scheduled_at.hour,
                minute=job.scheduled_at.minute,
            )
        elif job.repeat_type == RepeatType.MONTHLY:
            trigger = CronTrigger(
                day=job.scheduled_at.day,
                hour=job.scheduled_at.hour,
                minute=job.scheduled_at.minute,
            )
        else:
            trigger = DateTrigger(run_date=job.scheduled_at)

        self._scheduler.add_job(
            self._execute_job,
            trigger=trigger,
            id=job.id,
            args=[job.id],
            replace_existing=True,
        )

        self._save_jobs()
        logger.info(f"Job added: {job.id} ({job.job_type.value}) @ {job.display_time}")
        return job.id

    def remove_job(self, job_id: str) -> bool:
        """Remove a job.

        Args:
            job_id: ID of the job to remove.

        Returns:
            True on success.
        """
        if job_id not in self._jobs:
            return False

        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass

        job = self._jobs.pop(job_id)
        job.status = JobStatus.CANCELLED
        self._save_jobs()
        logger.info(f"Job removed: {job_id}")
        return True

    def get_jobs(self) -> list[ScheduledJob]:
        """Get all jobs.

        Returns:
            List of jobs.
        """
        return list(self._jobs.values())

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get a job by ID.

        Args:
            job_id: Job ID.

        Returns:
            The job, or None if not found.
        """
        return self._jobs.get(job_id)

    def _execute_job(self, job_id: str) -> None:
        """Execute a job.

        Args:
            job_id: ID of the job to execute.
        """
        job = self._jobs.get(job_id)
        if not job:
            logger.warning(f"Job not found: {job_id}")
            return

        job.status = JobStatus.RUNNING
        logger.info(f"Job started: {job_id} ({job.job_type.value})")

        try:
            if self._job_callback:
                self._job_callback(job)
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            logger.info(f"Job completed: {job_id}")

        except Exception as e:
            job.retry_count += 1
            if job.retry_count < self.settings.scheduler.max_retries:
                job.status = JobStatus.PENDING
                # Schedule retry
                retry_time = datetime.now() + timedelta(
                    seconds=self.settings.scheduler.retry_interval_sec
                )
                self._scheduler.add_job(
                    self._execute_job,
                    trigger=DateTrigger(run_date=retry_time),
                    id=f"{job_id}_retry_{job.retry_count}",
                    args=[job_id],
                )
                logger.warning(
                    f"Job {job_id} failed (retry {job.retry_count}/"
                    f"{self.settings.scheduler.max_retries}): {e}"
                )
            else:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                logger.error(f"Job {job_id} final failure: {e}")

        self._save_jobs()

    def _save_jobs(self) -> None:
        """Save job list to file."""
        self._jobs_file.parent.mkdir(parents=True, exist_ok=True)
        data = {jid: job.model_dump(mode="json") for jid, job in self._jobs.items()}
        with open(self._jobs_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def _load_jobs(self) -> None:
        """Restore job list from file."""
        if not self._jobs_file.exists():
            return

        try:
            with open(self._jobs_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for jid, job_data in data.items():
                job = ScheduledJob(**job_data)
                if job.status in (JobStatus.PENDING, JobStatus.RUNNING):
                    # Re-register incomplete jobs
                    job.status = JobStatus.PENDING
                    self._jobs[jid] = job
            logger.info(f"Restored {len(self._jobs)} jobs")
        except Exception as e:
            logger.error(f"Failed to restore jobs: {e}")
