"""ジョブ定義.

スケジュール投稿のジョブモデルを定義する。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class JobType(str, Enum):
    """ジョブの種類."""

    POST = "post"
    STORY = "story"


class JobStatus(str, Enum):
    """ジョブの状態."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RepeatType(str, Enum):
    """繰り返しの種類."""

    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ScheduledJob(BaseModel):
    """スケジュールジョブ.

    予約投稿やストーリー更新のスケジュールを表す。
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    job_type: JobType
    status: JobStatus = JobStatus.PENDING

    # スケジュール
    scheduled_at: datetime
    repeat_type: RepeatType = RepeatType.NONE

    # 投稿内容
    text: str = ""
    image_paths: list[str] = Field(default_factory=list)

    # メタデータ
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0

    @property
    def is_due(self) -> bool:
        """実行予定時刻を過ぎているか."""
        return datetime.now() >= self.scheduled_at and self.status == JobStatus.PENDING

    @property
    def display_time(self) -> str:
        """表示用の時刻文字列."""
        return self.scheduled_at.strftime("%Y/%m/%d %H:%M")

    @property
    def display_status(self) -> str:
        """表示用のステータス."""
        status_map = {
            JobStatus.PENDING: "待機中",
            JobStatus.RUNNING: "実行中",
            JobStatus.COMPLETED: "完了",
            JobStatus.FAILED: "失敗",
            JobStatus.CANCELLED: "キャンセル",
        }
        return status_map.get(self.status, str(self.status))
