"""投稿タブ.

投稿の作成・画像選択・予約設定を行うタブ。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDateTimeEdit,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import AppSettings
from src.scheduler.jobs import JobType, ScheduledJob

if TYPE_CHECKING:
    from src.browser.bridge import BrowserBridge


class ImagePreview(QWidget):
    """画像プレビューウィジェット."""

    removed = Signal(int)

    def __init__(self, image_path: Path, index: int, parent=None) -> None:
        super().__init__(parent)
        self.image_path = image_path
        self.index = index

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # サムネイル
        label = QLabel()
        pixmap = QPixmap(str(image_path))
        label.setPixmap(pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio))
        layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)

        # ファイル名
        name_label = QLabel(image_path.name)
        name_label.setStyleSheet("color: #999; font-size: 11px;")
        name_label.setMaximumWidth(150)
        layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 削除ボタン
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setStyleSheet(
            "QPushButton { background: #ef4444; color: white; border: none; border-radius: 12px; }"
        )
        remove_btn.clicked.connect(lambda: self.removed.emit(self.index))
        layout.addWidget(remove_btn, alignment=Qt.AlignmentFlag.AlignCenter)


class PostTab(QWidget):
    """投稿作成タブ."""

    # 予約ジョブを通知するシグナル
    post_scheduled = Signal(object)

    def __init__(
        self,
        settings: AppSettings,
        bridge: BrowserBridge | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self._bridge = bridge
        self._image_paths: list[Path] = []

        self.setAcceptDrops(True)
        self._setup_ui()
        self._connect_bridge_signals()

    def _setup_ui(self) -> None:
        """UIを構築."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # テキスト入力
        text_group = QGroupBox("投稿テキスト")
        text_layout = QVBoxLayout(text_group)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "VRChatでの出来事をシェアしよう… #ハッシュタグ @メンション 対応"
        )
        self.text_edit.setMaximumHeight(150)
        text_layout.addWidget(self.text_edit)

        layout.addWidget(text_group)

        # 画像選択
        image_group = QGroupBox("画像 (ドラッグ＆ドロップ対応)")
        image_layout = QVBoxLayout(image_group)

        # 画像追加ボタン
        btn_layout = QHBoxLayout()
        add_image_btn = QPushButton("画像を追加")
        add_image_btn.clicked.connect(self._select_images)
        btn_layout.addWidget(add_image_btn)

        clear_btn = QPushButton("全てクリア")
        clear_btn.clicked.connect(self._clear_images)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()

        self.image_count_label = QLabel("0 / 4 枚")
        btn_layout.addWidget(self.image_count_label)
        image_layout.addLayout(btn_layout)

        # 画像プレビューエリア
        self.image_preview_area = QWidget()
        self.image_preview_layout = QHBoxLayout(self.image_preview_area)
        self.image_preview_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(220)
        scroll.setWidget(self.image_preview_area)
        image_layout.addWidget(scroll)

        layout.addWidget(image_group)

        # 予約設定
        schedule_group = QGroupBox("予約投稿")
        schedule_layout = QVBoxLayout(schedule_group)

        self.schedule_check = QCheckBox("予約投稿にする")
        self.schedule_check.toggled.connect(self._toggle_schedule)
        schedule_layout.addWidget(self.schedule_check)

        schedule_time_layout = QHBoxLayout()
        schedule_time_layout.addWidget(QLabel("投稿日時:"))
        self.schedule_datetime = QDateTimeEdit()
        self.schedule_datetime.setCalendarPopup(True)
        self.schedule_datetime.setDateTime(datetime.now().replace(second=0, microsecond=0))
        self.schedule_datetime.setEnabled(False)
        schedule_time_layout.addWidget(self.schedule_datetime)
        schedule_time_layout.addStretch()
        schedule_layout.addLayout(schedule_time_layout)

        layout.addWidget(schedule_group)

        # 投稿ボタン
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.post_btn = QPushButton("投稿する")
        self.post_btn.setFixedSize(160, 40)
        self.post_btn.setStyleSheet(
            "QPushButton { background: #6366f1; color: white; border: none; "
            "border-radius: 8px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background: #818cf8; }"
        )
        self.post_btn.clicked.connect(self._on_post)
        btn_row.addWidget(self.post_btn)

        layout.addLayout(btn_row)
        layout.addStretch()

    def _select_images(self) -> None:
        """画像ファイルを選択."""
        max_images = self.settings.post.max_images
        remaining = max_images - len(self._image_paths)
        if remaining <= 0:
            QMessageBox.warning(self, "上限", f"画像は最大{max_images}枚までです")
            return

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "画像を選択",
            "",
            "画像ファイル (*.jpg *.jpeg *.png *.gif *.webp)",
        )

        for f in files[:remaining]:
            self._add_image(Path(f))

    def _add_image(self, path: Path) -> None:
        """画像を追加."""
        if len(self._image_paths) >= self.settings.post.max_images:
            return
        self._image_paths.append(path)
        self._update_image_previews()

    def _remove_image(self, index: int) -> None:
        """画像を削除."""
        if 0 <= index < len(self._image_paths):
            self._image_paths.pop(index)
            self._update_image_previews()

    def _clear_images(self) -> None:
        """全画像をクリア."""
        self._image_paths.clear()
        self._update_image_previews()

    def _update_image_previews(self) -> None:
        """画像プレビューを更新."""
        # 既存のプレビューを削除
        while self.image_preview_layout.count():
            item = self.image_preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 新しいプレビューを追加
        for i, path in enumerate(self._image_paths):
            preview = ImagePreview(path, i)
            preview.removed.connect(self._remove_image)
            self.image_preview_layout.addWidget(preview)

        self.image_preview_layout.addStretch()
        self.image_count_label.setText(
            f"{len(self._image_paths)} / {self.settings.post.max_images} 枚"
        )

    def _toggle_schedule(self, checked: bool) -> None:
        """予約投稿の切り替え."""
        self.schedule_datetime.setEnabled(checked)
        self.post_btn.setText("予約する" if checked else "投稿する")

    def _connect_bridge_signals(self) -> None:
        """ブリッジシグナルを接続する."""
        if self._bridge is None:
            return
        self._bridge.post_success.connect(self._on_post_success)
        self._bridge.post_failed.connect(self._on_post_failed)

    def _on_post_success(self, message: str) -> None:
        """投稿成功時の処理."""
        self.post_btn.setEnabled(True)
        self.post_btn.setText(
            "予約する" if self.schedule_check.isChecked() else "投稿する",
        )
        QMessageBox.information(self, "成功", message)
        # フォームクリア
        self.text_edit.clear()
        self._clear_images()
        self.schedule_check.setChecked(False)

    def _on_post_failed(self, message: str) -> None:
        """投稿失敗時の処理."""
        self.post_btn.setEnabled(True)
        self.post_btn.setText(
            "予約する" if self.schedule_check.isChecked() else "投稿する",
        )
        QMessageBox.warning(self, "エラー", message)

    def _on_post(self) -> None:
        """投稿ボタンクリック."""
        text = self.text_edit.toPlainText().strip()

        if not text and not self._image_paths:
            QMessageBox.warning(self, "入力エラー", "テキストまたは画像を入力してください")
            return

        scheduled_at = None
        if self.schedule_check.isChecked():
            scheduled_at = self.schedule_datetime.dateTime().toPython()
            if scheduled_at <= datetime.now():
                QMessageBox.warning(self, "日時エラー", "未来の日時を指定してください")
                return

        if scheduled_at:
            # 予約投稿: ScheduledJob を作成してシグナル発火
            job = ScheduledJob(
                job_type=JobType.POST,
                scheduled_at=scheduled_at,
                text=text,
                image_paths=[str(p) for p in self._image_paths],
            )
            self.post_scheduled.emit(job)
            logger.info(
                f"予約登録: {text[:30]}... "
                f"(画像: {len(self._image_paths)}枚)",
            )
            QMessageBox.information(self, "確認", "予約登録しました！")
            # フォームクリア
            self.text_edit.clear()
            self._clear_images()
            self.schedule_check.setChecked(False)
        elif self._bridge:
            # 即時投稿: ブリッジ経由で投稿
            self.post_btn.setEnabled(False)
            self.post_btn.setText("投稿中…")
            self._bridge.create_post(
                text=text,
                image_paths=self._image_paths or None,
            )
            logger.info(
                f"投稿: {text[:30]}... "
                f"(画像: {len(self._image_paths)}枚)",
            )
        else:
            # ブリッジ未接続時のフォールバック
            logger.info(
                f"投稿(テスト): {text[:30]}... "
                f"(画像: {len(self._image_paths)}枚)",
            )
            QMessageBox.information(
                self,
                "確認",
                "投稿しました！\n（テストモード: 実際の投稿は行われません）",
            )
            self.text_edit.clear()
            self._clear_images()
            self.schedule_check.setChecked(False)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """ドラッグ開始."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """ドロップ."""
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                self._add_image(path)
