"""スケジューラー ↔ ブラウザ接続.

SchedulerEngine からのジョブ実行を BrowserBridge に中継する。
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
    """スケジューラーとブラウザの接続.

    SchedulerEngine のコールバックとして登録し、
    ジョブ内容に応じて BrowserBridge を呼び出す。

    Events:
        job_started   (str)       : ジョブ実行開始
        job_completed (str)       : ジョブ実行完了
        job_failed    (str, str)  : ジョブ実行失敗 (id, error)
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

        # エンジンにコールバック登録
        self._engine.set_callback(self._execute_job)

    # ── パブリック ──

    def start(self) -> None:
        """スケジューラーを開始."""
        self._engine.start()

    def stop(self) -> None:
        """スケジューラーを停止."""
        self._engine.stop()

    def add_job(self, job: ScheduledJob) -> str:
        return self._engine.add_job(job)

    def remove_job(self, job_id: str) -> bool:
        return self._engine.remove_job(job_id)

    def get_jobs(self) -> list[ScheduledJob]:
        return self._engine.get_jobs()

    # ── 内部 ──

    def _execute_job(self, job: ScheduledJob) -> None:
        """ジョブを実行 (APScheduler スレッドプールから呼ばれる)."""
        self.emitter.emit("job_started", job.id)
        logger.info(f"ジョブ実行: {job.id} ({job.job_type.value})")

        try:
            if job.job_type == JobType.POST:
                self._execute_post(job)
            elif job.job_type == JobType.STORY:
                self._execute_story(job)
            self.emitter.emit("job_completed", job.id)
        except Exception as exc:
            msg = str(exc)
            logger.error(f"ジョブ失敗 {job.id}: {msg}")
            self.emitter.emit("job_failed", job.id, msg)
            raise

    def _execute_post(self, job: ScheduledJob) -> None:
        image_paths = job.image_paths if job.image_paths else None
        self._worker.create_post(text=job.text, image_paths=image_paths)

    def _execute_story(self, job: ScheduledJob) -> None:
        if not job.image_paths:
            raise ValueError("ストーリーには画像が必要です")
        self._worker.upload_story(
            image_path=job.image_paths[0],
            text=job.text or None,
        )
