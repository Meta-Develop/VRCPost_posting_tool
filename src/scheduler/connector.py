"""スケジューラーとブラウザの接続.

スケジュールされたジョブの実行時にブラウザ操作を呼び出す。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger
from PySide6.QtCore import QObject, Signal

from src.browser.bridge import BrowserBridge
from src.scheduler.engine import SchedulerEngine
from src.scheduler.jobs import JobType, ScheduledJob


class SchedulerConnector(QObject):
    """スケジューラーとブラウザブリッジを接続するコネクタ.

    SchedulerEngine がジョブを実行するタイミングで
    BrowserBridge を通じて投稿・ストーリー操作を行い、
    結果を GUI 向けシグナルとして発火する。
    """

    # --- シグナル定義 ---
    job_started = Signal(str)    # ジョブID
    job_completed = Signal(str)  # ジョブID
    job_failed = Signal(str, str)  # ジョブID, エラーメッセージ

    def __init__(
        self,
        engine: SchedulerEngine,
        bridge: BrowserBridge,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._engine = engine
        self._worker = bridge

        # エンジンにコールバックを登録
        self._engine.set_callback(self._execute_job)
        logger.info("SchedulerConnector: コールバック登録完了")

    # ------------------------------------------------------------------
    # コールバック
    # ------------------------------------------------------------------

    async def _execute_job(self, job: ScheduledJob) -> None:
        """SchedulerEngine から呼び出されるジョブ実行コールバック.

        ジョブ種別に応じて BrowserBridge の適切なメソッドを呼び出す。

        Args:
            job: 実行対象のスケジュールジョブ

        Raises:
            RuntimeError: ブラウザワーカーが停止している場合
        """
        if not self._worker.isRunning():
            msg = "BrowserBridge が動作していません"
            logger.error(f"SchedulerConnector: {msg}")
            raise RuntimeError(msg)

        self.job_started.emit(job.id)
        logger.info(
            f"SchedulerConnector: ジョブ実行開始 "
            f"{job.id} ({job.job_type.value})"
        )

        try:
            if job.job_type == JobType.POST:
                await self._execute_post(job)
            elif job.job_type == JobType.STORY:
                await self._execute_story(job)
            else:
                raise ValueError(f"未対応のジョブ種別: {job.job_type}")

            self.job_completed.emit(job.id)
            logger.info(f"SchedulerConnector: ジョブ完了 {job.id}")

        except Exception as exc:
            msg = str(exc)
            self.job_failed.emit(job.id, msg)
            logger.error(f"SchedulerConnector: ジョブ失敗 {job.id}: {msg}")
            raise

    # ------------------------------------------------------------------
    # ジョブ種別ごとの実行
    # ------------------------------------------------------------------

    async def _execute_post(self, job: ScheduledJob) -> None:
        """投稿ジョブを実行する.

        Args:
            job: 投稿ジョブ
        """
        image_paths = [Path(p) for p in job.image_paths] if job.image_paths else None
        self._worker.create_post(
            text=job.text,
            image_paths=image_paths,
        )

    async def _execute_story(self, job: ScheduledJob) -> None:
        """ストーリージョブを実行する.

        Args:
            job: ストーリージョブ

        Raises:
            ValueError: 画像パスが指定されていない場合
        """
        if not job.image_paths:
            raise ValueError("ストーリーには画像パスが必要です")

        image_path = Path(job.image_paths[0])
        self._worker.upload_story(
            image_path=image_path,
            text=job.text or None,
        )

    # ------------------------------------------------------------------
    # エンジン制御のショートカット
    # ------------------------------------------------------------------

    def start(self) -> None:
        """スケジューラーを開始する."""
        self._engine.start()
        logger.info("SchedulerConnector: スケジューラー開始")

    def stop(self) -> None:
        """スケジューラーを停止する."""
        self._engine.stop()
        logger.info("SchedulerConnector: スケジューラー停止")

    def add_job(self, job: ScheduledJob) -> str:
        """ジョブを追加する.

        Args:
            job: 追加するジョブ

        Returns:
            ジョブID
        """
        return self._engine.add_job(job)

    def remove_job(self, job_id: str) -> bool:
        """ジョブを削除する.

        Args:
            job_id: 削除対象のジョブID

        Returns:
            削除成功なら True
        """
        return self._engine.remove_job(job_id)

    def get_jobs(self) -> list[ScheduledJob]:
        """全ジョブを取得する.

        Returns:
            ジョブのリスト
        """
        return self._engine.get_jobs()
