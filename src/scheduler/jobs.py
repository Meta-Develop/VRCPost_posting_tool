"""Job definitions.

Defines models for scheduled posting jobs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class JobType(str, Enum):
    """Job type."""

    POST = "post"
    STORY = "story"


class JobStatus(str, Enum):
    """Job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RepeatType(str, Enum):
    """Repeat type."""

    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ScheduledJob(BaseModel):
    """Scheduled job.

    Represents a scheduled post or story update.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    job_type: JobType
    status: JobStatus = JobStatus.PENDING

    # Schedule
    scheduled_at: datetime
    repeat_type: RepeatType = RepeatType.NONE

    # Post content
    text: str = ""
    image_paths: list[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0

    @property
    def is_due(self) -> bool:
        """Whether the scheduled time has passed."""
        return datetime.now() >= self.scheduled_at and self.status == JobStatus.PENDING

    @property
    def display_time(self) -> str:
        """Formatted time for display."""
        return self.scheduled_at.strftime("%Y/%m/%d %H:%M")

    @property
    def display_status(self) -> str:
        """Localized status for display."""
        status_map = {
            JobStatus.PENDING: "Pending",
            JobStatus.RUNNING: "Running",
            JobStatus.COMPLETED: "Completed",
            JobStatus.FAILED: "Failed",
            JobStatus.CANCELLED: "Cancelled",
        }
        return status_map.get(self.status, str(self.status))
