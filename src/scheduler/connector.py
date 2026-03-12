"""Scheduler-browser connector.

Relays job execution from SchedulerEngine to BrowserBridge.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.scheduler.jobs import JobType, ScheduledJob

if TYPE_CHECKING:
    from src.browser.bridge import BrowserBridge
    from src.gui.events import EventEmitter
    from src.scheduler.engine import SchedulerEngine


class SchedulerConnector:
    """Connector between the scheduler and browser.

    Registered as a callback on SchedulerEngine and
    invokes BrowserBridge according to job type.

    Events:
        job_started   (str)       : Job execution started
        job_completed (str)       : Job execution completed
        job_failed    (str, str)  : Job execution failed (id, error)
    """

    def __init__(
        self,
        engine: SchedulerEngine,
        worker: BrowserBridge,
        emitter: EventEmitter,
    ) -> None:
        self._engine = engine
        self._worker = worker
        self.emitter = emitter

        # Register callback on the engine
        self._engine.set_callback(self._execute_job)

    # ── Public ──

    def start(self) -> None:
        """Start the scheduler."""
        self._engine.start()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._engine.stop()

    def add_job(self, job: ScheduledJob) -> str:
        return self._engine.add_job(job)

    def remove_job(self, job_id: str) -> bool:
        return self._engine.remove_job(job_id)

    def get_jobs(self) -> list[ScheduledJob]:
        return self._engine.get_jobs()

    # ── Internal ──

    def _execute_job(self, job: ScheduledJob) -> None:
        """Execute a job (called from APScheduler thread pool)."""
        self.emitter.emit("job_started", job.id)
        logger.info(f"Job executing: {job.id} ({job.job_type.value})")

        try:
            if job.job_type == JobType.POST:
                self._execute_post(job)
            elif job.job_type == JobType.STORY:
                self._execute_story(job)
            self.emitter.emit("job_completed", job.id)
        except Exception as exc:
            msg = str(exc)
            logger.error(f"Job failed {job.id}: {msg}")
            self.emitter.emit("job_failed", job.id, msg)
            raise

    def _execute_post(self, job: ScheduledJob) -> None:
        image_paths = job.image_paths if job.image_paths else None
        self._worker.create_post(text=job.text, image_paths=image_paths)

    def _execute_story(self, job: ScheduledJob) -> None:
        if not job.image_paths:
            raise ValueError("Stories require an image")
        self._worker.upload_story(
            image_path=job.image_paths[0],
            text=job.text or None,
        )
