"""ストーリータブ.

ストーリーのアップロード・スケジュール管理を行うタブ。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDateTimeEdit,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import AppSettings


class StoryTab(QWidget):
    """ストーリー管理タブ."""

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._image_path: Optional[Path] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UIを構築."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # ストーリー画像
        image_group = QGroupBox("ストーリー画像")
        image_layout = QVBoxLayout(image_group)

        select_layout = QHBoxLayout()
        self.select_btn = QPushButton("画像を選択")
        self.select_btn.clicked.connect(self._select_image)
        select_layout.addWidget(self.select_btn)

        self.filename_label = QLabel("未選択")
        self.filename_label.setStyleSheet("color: #999;")
        select_layout.addWidget(self.filename_label)
        select_layout.addStretch()
        image_layout.addLayout(select_layout)

        # プレビュー
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setStyleSheet(
            "QLabel { background: #1a1a1a; border: 2px dashed #333; border-radius: 8px; }"
        )
        self.preview_label.setText("画像を選択またはドラッグ＆ドロップ")
        image_layout.addWidget(self.preview_label)

        layout.addWidget(image_group)

        # テキスト
        text_group = QGroupBox("テキスト（任意）")
        text_layout = QVBoxLayout(text_group)
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("ストーリーのテキスト...")
        text_layout.addWidget(self.text_input)
        layout.addWidget(text_group)

        # スケジュール設定
        schedule_group = QGroupBox("定期更新")
        schedule_layout = QVBoxLayout(schedule_group)

        self.schedule_check = QCheckBox("定期更新を有効にする")
        schedule_layout.addWidget(self.schedule_check)

        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("更新時間:"))
        self.update_time = QDateTimeEdit()
        self.update_time.setDisplayFormat("HH:mm")
        self.update_time.setDateTime(datetime.now().replace(hour=12, minute=0))
        time_layout.addWidget(self.update_time)
        time_layout.addStretch()
        schedule_layout.addLayout(time_layout)

        layout.addWidget(schedule_group)

        # アクションボタン
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.upload_btn = QPushButton("ストーリーを投稿")
        self.upload_btn.setFixedSize(180, 40)
        self.upload_btn.setStyleSheet(
            "QPushButton { background: #6366f1; color: white; border: none; "
            "border-radius: 8px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background: #818cf8; }"
        )
        self.upload_btn.clicked.connect(self._on_upload)
        btn_row.addWidget(self.upload_btn)

        layout.addLayout(btn_row)
        layout.addStretch()

    def _select_image(self) -> None:
        """画像を選択."""
        file, _ = QFileDialog.getOpenFileName(
            self, "ストーリー画像を選択", "", "画像ファイル (*.jpg *.jpeg *.png *.gif *.webp)"
        )
        if file:
            self._set_image(Path(file))

    def _set_image(self, path: Path) -> None:
        """画像を設定."""
        self._image_path = path
        self.filename_label.setText(path.name)

        pixmap = QPixmap(str(path))
        scaled = pixmap.scaled(
            400, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)

    def _on_upload(self) -> None:
        """アップロードボタンクリック."""
        if not self._image_path:
            QMessageBox.warning(self, "エラー", "画像を選択してください")
            return

        _text = self.text_input.text().strip()  # noqa: F841

        # TODO: ブラウザ自動操作でストーリーをアップロード
        logger.info(f"ストーリー投稿: {self._image_path.name}")

        QMessageBox.information(
            self, "確認", "ストーリーを投稿しました！\n（テストモード: 実際の投稿は行われません）"
        )

        # フォームリセット
        self._image_path = None
        self.filename_label.setText("未選択")
        self.preview_label.clear()
        self.preview_label.setText("画像を選択またはドラッグ＆ドロップ")
        self.text_input.clear()
