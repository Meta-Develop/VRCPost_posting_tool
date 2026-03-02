"""スケジューラーエンジン.

APSchedulerを使ってジョブの実行スケジュールを管理する。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from loguru import logger

from src.config.settings import AppSettings
from src.scheduler.jobs import JobStatus, RepeatType, ScheduledJob


class SchedulerEngine:
    """スケジューラーエンジン.

    ジョブの登録・実行・永続化を管理する。
    """

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self._scheduler = AsyncIOScheduler(timezone=settings.scheduler.timezone)
        self._jobs: dict[str, ScheduledJob] = {}
        self._job_callback: Optional[Callable] = None
        self._jobs_file = Path(settings.scheduler.jobs_file)

    def set_callback(self, callback: Callable) -> None:
        """ジョブ実行時のコールバックを設定.

        Args:
            callback: ジョブを受け取って実行する非同期関数
        """
        self._job_callback = callback

    def start(self) -> None:
        """スケジューラーを開始."""
        self._load_jobs()
        self._scheduler.start()
        logger.info(f"スケジューラー開始 (ジョブ数: {len(self._jobs)})")

    def stop(self) -> None:
        """スケジューラーを停止."""
        self._save_jobs()
        if self._scheduler.running:
            self._scheduler.shutdown()
        logger.info("スケジューラー停止")

    def add_job(self, job: ScheduledJob) -> str:
        """ジョブを追加.

        Args:
            job: 追加するジョブ

        Returns:
            ジョブID
        """
        self._jobs[job.id] = job

        # APSchedulerにジョブを登録
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
        logger.info(f"ジョブ追加: {job.id} ({job.job_type.value}) @ {job.display_time}")
        return job.id

    def remove_job(self, job_id: str) -> bool:
        """ジョブを削除.

        Args:
            job_id: 削除するジョブのID

        Returns:
            削除成功ならTrue
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
        logger.info(f"ジョブ削除: {job_id}")
        return True

    def get_jobs(self) -> list[ScheduledJob]:
        """全ジョブを取得.

        Returns:
            ジョブのリスト
        """
        return list(self._jobs.values())

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """ジョブを取得.

        Args:
            job_id: ジョブID

        Returns:
            ジョブ（存在しない場合None）
        """
        return self._jobs.get(job_id)

    async def _execute_job(self, job_id: str) -> None:
        """ジョブを実行.

        Args:
            job_id: 実行するジョブのID
        """
        job = self._jobs.get(job_id)
        if not job:
            logger.warning(f"ジョブが見つかりません: {job_id}")
            return

        job.status = JobStatus.RUNNING
        logger.info(f"ジョブ実行開始: {job_id} ({job.job_type.value})")

        try:
            if self._job_callback:
                await self._job_callback(job)
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            logger.info(f"ジョブ実行完了: {job_id}")

        except Exception as e:
            job.retry_count += 1
            if job.retry_count < self.settings.scheduler.max_retries:
                job.status = JobStatus.PENDING
                # リトライスケジュール
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
                    f"ジョブ {job_id} 失敗 (リトライ {job.retry_count}/"
                    f"{self.settings.scheduler.max_retries}): {e}"
                )
            else:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                logger.error(f"ジョブ {job_id} 最終失敗: {e}")

        self._save_jobs()

    def _save_jobs(self) -> None:
        """ジョブ一覧をファイルに保存."""
        self._jobs_file.parent.mkdir(parents=True, exist_ok=True)
        data = {jid: job.model_dump(mode="json") for jid, job in self._jobs.items()}
        with open(self._jobs_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def _load_jobs(self) -> None:
        """ファイルからジョブ一覧を復元."""
        if not self._jobs_file.exists():
            return

        try:
            with open(self._jobs_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for jid, job_data in data.items():
                job = ScheduledJob(**job_data)
                if job.status in (JobStatus.PENDING, JobStatus.RUNNING):
                    # 未完了ジョブを再登録
                    job.status = JobStatus.PENDING
                    self._jobs[jid] = job
            logger.info(f"ジョブ {len(self._jobs)}件 を復元")
        except Exception as e:
            logger.error(f"ジョブの復元に失敗: {e}")
