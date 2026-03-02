"""ランダム投稿タブ.

指定ディレクトリから未使用画像をランダムに選んで投稿する。
使用済み画像は自動追跡され、同じ画像が二度投稿されることはない。
"""

from __future__ import annotations

import random
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import AppSettings
from src.scheduler.jobs import JobType, RepeatType, ScheduledJob
from src.utils.image_history import ImageHistory

if TYPE_CHECKING:
    from src.browser.bridge import BrowserBridge

# スタイル定数
_BTN_PRIMARY = (
    "QPushButton { background: #6366f1; color: white; border: none; "
    "border-radius: 8px; font-size: 14px; font-weight: bold; }"
    "QPushButton:hover { background: #818cf8; }"
    "QPushButton:disabled { background: #555; }"
)
_BTN_DANGER = (
    "QPushButton { background: #ef4444; color: white; border: none; "
    "border-radius: 6px; font-size: 12px; }"
    "QPushButton:hover { background: #f87171; }"
)
_BTN_SECONDARY = (
    "QPushButton { background: #374151; color: white; border: none; "
    "border-radius: 6px; font-size: 12px; }"
    "QPushButton:hover { background: #4b5563; }"
)


class RandomPostTab(QWidget):
    """ランダム画像投稿タブ.

    ディレクトリを指定して、未使用画像をランダムに選択し投稿する。
    """

    # スケジュール登録時に発火
    post_scheduled = Signal(object)
    # 画像残数が少なくなったとき (dir_path, remaining, total)
    images_running_low = Signal(str, int, int)

    def __init__(
        self,
        settings: AppSettings,
        bridge: BrowserBridge | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self._bridge = bridge
        self._history = ImageHistory()
        self._current_dir: Path | None = None
        self._preview_path: Path | None = None
        self._auto_posting = False
        self._low_image_threshold = 5

        # 自動投稿タイマー
        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._auto_post_tick)

        self._setup_ui()
        self._connect_bridge_signals()

    # ── UI構築 ────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # --- ディレクトリ選択 ---
        dir_group = QGroupBox("画像フォルダ")
        dir_layout = QVBoxLayout(dir_group)

        dir_row = QHBoxLayout()
        self._dir_label = QLabel("未選択")
        self._dir_label.setStyleSheet("color: #999;")
        dir_row.addWidget(self._dir_label, 1)

        browse_btn = QPushButton("フォルダを選択")
        browse_btn.clicked.connect(self._select_directory)
        dir_row.addWidget(browse_btn)
        dir_layout.addLayout(dir_row)

        # 統計
        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        dir_layout.addWidget(self._stats_label)

        layout.addWidget(dir_group)

        # --- プレビュー ---
        preview_group = QGroupBox("プレビュー")
        preview_layout = QVBoxLayout(preview_group)

        self._preview_image = QLabel("ここに選択された画像が表示されます")
        self._preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_image.setMinimumHeight(200)
        self._preview_image.setStyleSheet(
            "QLabel { background: #1f2937; border-radius: 8px; color: #6b7280; }"
        )
        preview_layout.addWidget(self._preview_image)

        self._preview_name = QLabel("")
        self._preview_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_name.setStyleSheet("color: #d1d5db; font-size: 12px;")
        preview_layout.addWidget(self._preview_name)

        preview_btn_row = QHBoxLayout()
        self._shuffle_btn = QPushButton("シャッフル (別の画像)")
        self._shuffle_btn.setStyleSheet(_BTN_SECONDARY)
        self._shuffle_btn.clicked.connect(self._pick_random)
        self._shuffle_btn.setEnabled(False)
        preview_btn_row.addWidget(self._shuffle_btn)

        self._skip_btn = QPushButton("この画像をスキップ")
        self._skip_btn.setStyleSheet(_BTN_DANGER)
        self._skip_btn.clicked.connect(self._skip_current)
        self._skip_btn.setEnabled(False)
        preview_btn_row.addWidget(self._skip_btn)
        preview_btn_row.addStretch()
        preview_layout.addLayout(preview_btn_row)

        layout.addWidget(preview_group)

        # --- テキスト ---
        text_group = QGroupBox("投稿テキスト (任意)")
        text_layout = QVBoxLayout(text_group)
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText("投稿に添えるテキスト")
        self._text_edit.setMaximumHeight(80)
        text_layout.addWidget(self._text_edit)
        layout.addWidget(text_group)

        # --- 画像枚数 ---
        count_row = QHBoxLayout()
        count_row.addWidget(QLabel("一度に投稿する画像枚数:"))
        self._count_spin = QSpinBox()
        self._count_spin.setRange(1, 4)
        self._count_spin.setValue(1)
        count_row.addWidget(self._count_spin)
        count_row.addStretch()
        layout.addLayout(count_row)

        # --- 自動投稿 ---
        auto_group = QGroupBox("自動ランダム投稿")
        auto_layout = QVBoxLayout(auto_group)

        auto_desc = QLabel(
            "ONにすると、指定間隔で未使用画像を自動的にランダム投稿します。"
        )
        auto_desc.setStyleSheet("color: #9ca3af; font-size: 12px;")
        auto_desc.setWordWrap(True)
        auto_layout.addWidget(auto_desc)

        auto_row = QHBoxLayout()
        self._auto_check = QCheckBox("自動投稿を有効にする")
        self._auto_check.toggled.connect(self._toggle_auto_post)
        auto_row.addWidget(self._auto_check)

        auto_row.addWidget(QLabel("間隔:"))
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 1440)
        self._interval_spin.setValue(60)
        self._interval_spin.setSuffix(" 分")
        auto_row.addWidget(self._interval_spin)

        auto_row.addWidget(QLabel("画像残:"))
        self._threshold_spin = QSpinBox()
        self._threshold_spin.setRange(1, 100)
        self._threshold_spin.setValue(5)
        self._threshold_spin.setSuffix(" 枚で通知")
        self._threshold_spin.valueChanged.connect(self._on_threshold_changed)
        auto_row.addWidget(self._threshold_spin)

        auto_row.addStretch()
        auto_layout.addLayout(auto_row)

        self._auto_status_label = QLabel("")
        self._auto_status_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        auto_layout.addWidget(self._auto_status_label)

        layout.addWidget(auto_group)

        # --- 予約設定 ---
        schedule_group = QGroupBox("スケジュール (任意)")
        schedule_layout = QVBoxLayout(schedule_group)

        self._schedule_check = QCheckBox("予約投稿にする")
        self._schedule_check.toggled.connect(self._toggle_schedule)
        schedule_layout.addWidget(self._schedule_check)

        sched_row = QHBoxLayout()
        sched_row.addWidget(QLabel("日時:"))
        self._schedule_dt = QDateTimeEdit()
        self._schedule_dt.setCalendarPopup(True)
        self._schedule_dt.setDateTime(datetime.now().replace(second=0, microsecond=0))
        self._schedule_dt.setEnabled(False)
        sched_row.addWidget(self._schedule_dt)

        sched_row.addWidget(QLabel("繰り返し:"))
        self._repeat_combo = QComboBox()
        self._repeat_combo.addItems(["なし", "毎日", "毎週", "毎月"])
        self._repeat_combo.setEnabled(False)
        sched_row.addWidget(self._repeat_combo)
        sched_row.addStretch()
        schedule_layout.addLayout(sched_row)

        layout.addWidget(schedule_group)

        # --- アクションボタン ---
        btn_row = QHBoxLayout()

        reset_btn = QPushButton("履歴リセット")
        reset_btn.setStyleSheet(_BTN_DANGER)
        reset_btn.setFixedHeight(36)
        reset_btn.clicked.connect(self._reset_history)
        btn_row.addWidget(reset_btn)

        btn_row.addStretch()

        self._post_btn = QPushButton("ランダム投稿")
        self._post_btn.setFixedSize(180, 40)
        self._post_btn.setStyleSheet(_BTN_PRIMARY)
        self._post_btn.clicked.connect(self._on_post)
        self._post_btn.setEnabled(False)
        btn_row.addWidget(self._post_btn)

        layout.addLayout(btn_row)
        layout.addStretch()

    # ── ディレクトリ選択 ──────────────────────────────

    def _select_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "画像フォルダを選択")
        if not directory:
            return
        self._current_dir = Path(directory)
        self._dir_label.setText(str(self._current_dir))
        self._dir_label.setStyleSheet("color: #d1d5db;")
        self._update_stats()
        self._pick_random()

    def _update_stats(self) -> None:
        if not self._current_dir:
            return
        total, used, unused = self._history.get_stats(self._current_dir)
        self._stats_label.setText(
            f"全 {total} 枚 ─ 投稿済 {used} 枚 ─ 未使用 {unused} 枚"
        )
        has_unused = unused > 0
        self._post_btn.setEnabled(has_unused)
        self._shuffle_btn.setEnabled(has_unused)

    # ── プレビュー / シャッフル ───────────────────────

    def _pick_random(self) -> None:
        """未使用画像を1枚ランダムに選んでプレビュー表示する.

        ※ この段階では使用済みにしない（投稿時に記録する）
        """
        if not self._current_dir:
            return

        # pick_unused は履歴に記録してしまうので、内部の _get_unused を使う
        unused = self._history._get_unused(self._current_dir)
        if not unused:
            self._preview_image.setText("未使用画像がありません")
            self._preview_name.setText("")
            self._preview_path = None
            self._skip_btn.setEnabled(False)
            self._update_stats()
            return

        chosen = random.choice(unused)
        self._show_preview(chosen)

    def _show_preview(self, path: Path) -> None:
        self._preview_path = path
        pixmap = QPixmap(str(path))
        scaled = pixmap.scaled(
            400, 300,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_image.setPixmap(scaled)
        self._preview_name.setText(path.name)
        self._skip_btn.setEnabled(True)

    def _skip_current(self) -> None:
        """現在プレビュー中の画像を使用済みにしてスキップ."""
        if not self._current_dir or not self._preview_path:
            return
        self._history.mark_used(self._current_dir, self._preview_path.name)
        logger.info(f"スキップ: {self._preview_path.name}")
        self._update_stats()
        self._pick_random()

    # ── スケジュール切替 ─────────────────────────────

    def _toggle_schedule(self, checked: bool) -> None:
        self._schedule_dt.setEnabled(checked)
        self._repeat_combo.setEnabled(checked)
        self._post_btn.setText("予約する" if checked else "ランダム投稿")

    # ── 投稿 ──────────────────────────────────────────

    def _on_post(self) -> None:
        if not self._current_dir:
            QMessageBox.warning(self, "エラー", "フォルダを選択してください")
            return

        count = self._count_spin.value()
        images = self._history.pick_unused(self._current_dir, count)
        if not images:
            QMessageBox.warning(self, "エラー", "未使用の画像がありません")
            return

        text = self._text_edit.toPlainText().strip()

        # 予約投稿
        if self._schedule_check.isChecked():
            scheduled_at = self._schedule_dt.dateTime().toPython()
            if scheduled_at <= datetime.now():
                QMessageBox.warning(self, "日時エラー", "未来の日時を指定してください")
                return

            repeat_map = {
                0: RepeatType.NONE,
                1: RepeatType.DAILY,
                2: RepeatType.WEEKLY,
                3: RepeatType.MONTHLY,
            }
            repeat = repeat_map.get(self._repeat_combo.currentIndex(), RepeatType.NONE)

            job = ScheduledJob(
                job_type=JobType.POST,
                scheduled_at=scheduled_at,
                repeat_type=repeat,
                text=text,
                image_paths=[str(p) for p in images],
            )
            self.post_scheduled.emit(job)
            logger.info(f"ランダム予約登録: {[p.name for p in images]}")
            QMessageBox.information(self, "確認", "ランダム投稿を予約しました！")
        elif self._bridge:
            # 即時投稿
            self._post_btn.setEnabled(False)
            self._post_btn.setText("投稿中…")
            self._bridge.create_post(text=text, image_paths=images)
            logger.info(f"ランダム即時投稿: {[p.name for p in images]}")
        else:
            logger.info(f"ランダム投稿(テスト): {[p.name for p in images]}")
            QMessageBox.information(
                self, "確認",
                f"ランダム投稿しました！\n画像: {', '.join(p.name for p in images)}"
                "\n（テストモード: 実際の投稿は行われません）",
            )

        self._update_stats()
        self._pick_random()
        self._check_low_images()

    # ── 自動投稿 ─────────────────────────────────────

    def _toggle_auto_post(self, checked: bool) -> None:
        """自動投稿の有効/無効を切り替え."""
        if checked:
            if not self._current_dir:
                QMessageBox.warning(self, "エラー", "先にフォルダを選択してください")
                self._auto_check.setChecked(False)
                return
            interval_ms = self._interval_spin.value() * 60 * 1000
            self._auto_timer.start(interval_ms)
            self._auto_posting = True
            self._interval_spin.setEnabled(False)
            self._auto_status_label.setText(
                f"自動投稿 ON ─ {self._interval_spin.value()}分間隔"
            )
            self._auto_status_label.setStyleSheet("color: #22c55e; font-size: 12px;")
            logger.info(f"自動投稿開始: {self._interval_spin.value()}分間隔")
        else:
            self._auto_timer.stop()
            self._auto_posting = False
            self._interval_spin.setEnabled(True)
            self._auto_status_label.setText("自動投稿 OFF")
            self._auto_status_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
            logger.info("自動投稿停止")

    def _auto_post_tick(self) -> None:
        """自動投稿タイマーのティック."""
        if not self._current_dir or not self._bridge:
            return

        count = self._count_spin.value()
        images = self._history.pick_unused(self._current_dir, count)
        if not images:
            self._auto_check.setChecked(False)
            logger.warning("自動投稿: 未使用画像がなくなったため停止")
            return

        text = self._text_edit.toPlainText().strip()
        self._bridge.create_post(text=text, image_paths=images)
        logger.info(f"自動投稿: {[p.name for p in images]}")

        self._update_stats()
        self._pick_random()
        self._check_low_images()

    def _on_threshold_changed(self, value: int) -> None:
        self._low_image_threshold = value

    def _check_low_images(self) -> None:
        """未使用画像が閾値以下なら警告シグナルを発火."""
        if not self._current_dir:
            return
        total, _used, remaining = self._history.get_stats(self._current_dir)
        if total > 0 and remaining <= self._low_image_threshold:
            self.images_running_low.emit(
                str(self._current_dir), remaining, total,
            )

    # ── 履歴リセット ─────────────────────────────────

    def _reset_history(self) -> None:
        if not self._current_dir:
            QMessageBox.warning(self, "エラー", "フォルダを選択してください")
            return
        reply = QMessageBox.question(
            self, "確認",
            f"{self._current_dir.name} の使用履歴をリセットしますか？\n"
            "すべての画像が「未使用」に戻ります。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._history.reset(self._current_dir)
            self._update_stats()
            self._pick_random()
            QMessageBox.information(self, "完了", "履歴をリセットしました")

    # ── ブリッジシグナル ─────────────────────────────

    def _connect_bridge_signals(self) -> None:
        if self._bridge is None:
            return
        self._bridge.post_success.connect(self._on_post_success)
        self._bridge.post_failed.connect(self._on_post_failed)

    def _on_post_success(self, message: str) -> None:
        self._post_btn.setEnabled(True)
        self._post_btn.setText(
            "予約する" if self._schedule_check.isChecked() else "ランダム投稿",
        )
        QMessageBox.information(self, "成功", message)

    def _on_post_failed(self, message: str) -> None:
        self._post_btn.setEnabled(True)
        self._post_btn.setText(
            "予約する" if self._schedule_check.isChecked() else "ランダム投稿",
        )
        QMessageBox.warning(self, "エラー", message)
