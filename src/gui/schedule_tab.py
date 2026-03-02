"""スケジュール管理タブ.

予約投稿・定期投稿のスケジュールを一覧表示・管理するタブ。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import AppSettings

if TYPE_CHECKING:
    from src.scheduler.connector import SchedulerConnector


class ScheduleTab(QWidget):
    """スケジュール管理タブ."""

    def __init__(
        self,
        settings: AppSettings,
        connector: SchedulerConnector | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self._connector = connector
        self._setup_ui()
        self._connect_connector_signals()

        # 30秒ごとにスケジュール一覧を更新
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_schedule)
        self._refresh_timer.start(30000)

        # 初回読み込み
        self._refresh_schedule()

    def _setup_ui(self) -> None:
        """UIを構築."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # ヘッダー
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("予約投稿一覧"))
        header_layout.addStretch()

        refresh_btn = QPushButton("更新")
        refresh_btn.clicked.connect(self._refresh_schedule)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # スケジュールテーブル
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "種類", "予定日時", "テキスト", "画像数", "状態"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table)

        # アクションボタン
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("選択したジョブをキャンセル")
        cancel_btn.clicked.connect(self._cancel_selected)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        # ステータス
        self.status_label = QLabel("ジョブ: 0件")
        self.status_label.setStyleSheet("color: #999;")
        layout.addWidget(self.status_label)

    def _connect_connector_signals(self) -> None:
        """コネクタシグナルを接続する."""
        if self._connector is None:
            return
        self._connector.job_started.connect(self._on_job_started)
        self._connector.job_completed.connect(self._on_job_completed)
        self._connector.job_failed.connect(self._on_job_failed)

    def _on_job_started(self, job_id: str) -> None:
        """ジョブ開始時にテーブルのステータスを更新."""
        self._update_job_status(job_id, "実行中")

    def _on_job_completed(self, job_id: str) -> None:
        """ジョブ完了時にテーブルのステータスを更新."""
        self._update_job_status(job_id, "完了")

    def _on_job_failed(self, job_id: str, _message: str) -> None:
        """ジョブ失敗時にテーブルのステータスを更新."""
        self._update_job_status(job_id, "失敗")

    def _update_job_status(self, job_id: str, status: str) -> None:
        """テーブル内の指定ジョブのステータスを更新."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == job_id:
                self.table.setItem(row, 5, QTableWidgetItem(status))
                break

    def refresh_schedule(self) -> None:
        """外部から呼び出し可能なスケジュール更新."""
        self._refresh_schedule()

    def _refresh_schedule(self) -> None:
        """スケジュール一覧を更新."""
        self.table.setRowCount(0)

        if self._connector:
            jobs = self._connector.get_jobs()
            for job in jobs:
                self.add_job_to_table(
                    job_id=job.id,
                    job_type=job.job_type.value,
                    scheduled_at=job.display_time,
                    text=job.text,
                    image_count=len(job.image_paths),
                    status=job.display_status,
                )

        self.status_label.setText(f"ジョブ: {self.table.rowCount()}件")
        logger.debug("スケジュール一覧を更新")

    def add_job_to_table(
        self,
        job_id: str,
        job_type: str,
        scheduled_at: str,
        text: str,
        image_count: int,
        status: str,
    ) -> None:
        """テーブルにジョブを追加.

        Args:
            job_id: ジョブID
            job_type: ジョブ種類
            scheduled_at: 予定日時
            text: テキスト
            image_count: 画像数
            status: ステータス
        """
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(job_id))
        self.table.setItem(row, 1, QTableWidgetItem(job_type))
        self.table.setItem(row, 2, QTableWidgetItem(scheduled_at))
        self.table.setItem(row, 3, QTableWidgetItem(text[:50]))
        self.table.setItem(row, 4, QTableWidgetItem(str(image_count)))
        self.table.setItem(row, 5, QTableWidgetItem(status))

        self.status_label.setText(f"ジョブ: {self.table.rowCount()}件")

    def _cancel_selected(self) -> None:
        """選択したジョブをキャンセル."""
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "選択エラー", "キャンセルするジョブを選択してください")
            return

        row = selected[0].row()
        job_id = self.table.item(row, 0).text()

        reply = QMessageBox.question(
            self,
            "確認",
            f"ジョブ {job_id} をキャンセルしますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self._connector:
                self._connector.remove_job(job_id)
            self.table.removeRow(row)
            self.status_label.setText(f"ジョブ: {self.table.rowCount()}件")
            logger.info(f"ジョブキャンセル: {job_id}")
