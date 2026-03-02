"""設定タブ.

アプリケーションの設定を管理するタブ。
"""

from __future__ import annotations

from loguru import logger
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import AppSettings


class SettingsTab(QWidget):
    """設定管理タブ."""

    settings_changed = Signal()

    def __init__(
        self,
        settings: AppSettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()
        self._load_values()
        self._connect_signals()
        logger.debug("設定タブを初期化しました")

    # ------------------------------------------------------------------
    # UI構築
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """UIを構築."""
        root = QVBoxLayout(self)

        # ─── 接続設定 ──────────────────────────────────────
        conn_group = QGroupBox("接続設定")
        conn_form = QFormLayout(conn_group)

        self._test_mode_cb = QCheckBox("テストモードを使用する")
        conn_form.addRow(self._test_mode_cb)

        self._test_server_url = QLineEdit()
        conn_form.addRow("テストサーバURL:", self._test_server_url)

        self._base_url = QLineEdit()
        self._base_url.setReadOnly(True)
        conn_form.addRow("本番URL:", self._base_url)

        self._active_url_label = QLabel()
        self._active_url_label.setStyleSheet(
            "color: #6366f1; font-weight: bold;"
        )
        conn_form.addRow("アクティブURL:", self._active_url_label)

        root.addWidget(conn_group)

        # ─── ブラウザ設定 ──────────────────────────────────
        browser_group = QGroupBox("ブラウザ設定")
        browser_form = QFormLayout(browser_group)

        self._headless_cb = QCheckBox("ヘッドレスモード")
        browser_form.addRow(self._headless_cb)

        self._timeout_ms = QSpinBox()
        self._timeout_ms.setRange(1000, 120000)
        self._timeout_ms.setSingleStep(1000)
        self._timeout_ms.setSuffix(" ms")
        browser_form.addRow("タイムアウト:", self._timeout_ms)

        self._slow_mo = QSpinBox()
        self._slow_mo.setRange(0, 5000)
        self._slow_mo.setSingleStep(50)
        self._slow_mo.setSuffix(" ms")
        browser_form.addRow("スローモーション:", self._slow_mo)

        root.addWidget(browser_group)

        # ─── 投稿設定 ──────────────────────────────────────
        post_group = QGroupBox("投稿設定")
        post_form = QFormLayout(post_group)

        self._max_images = QSpinBox()
        self._max_images.setRange(1, 20)
        post_form.addRow("最大画像数:", self._max_images)

        self._image_max_kb = QSpinBox()
        self._image_max_kb.setRange(256, 51200)
        self._image_max_kb.setSingleStep(256)
        self._image_max_kb.setSuffix(" KB")
        post_form.addRow("画像最大サイズ:", self._image_max_kb)

        root.addWidget(post_group)

        # ─── スケジューラー設定 ────────────────────────────
        sched_group = QGroupBox("スケジューラー設定")
        sched_form = QFormLayout(sched_group)

        self._timezone_label = QLabel()
        sched_form.addRow("タイムゾーン:", self._timezone_label)

        self._max_retries = QSpinBox()
        self._max_retries.setRange(0, 10)
        sched_form.addRow("最大リトライ回数:", self._max_retries)

        self._retry_interval = QSpinBox()
        self._retry_interval.setRange(10, 600)
        self._retry_interval.setSingleStep(10)
        self._retry_interval.setSuffix(" 秒")
        sched_form.addRow("リトライ間隔:", self._retry_interval)

        root.addWidget(sched_group)

        # ─── ボタン行 ──────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._reset_btn = QPushButton("デフォルトに戻す")
        btn_row.addWidget(self._reset_btn)

        self._save_btn = QPushButton("保存")
        self._save_btn.setStyleSheet(
            "QPushButton { background: #6366f1; color: white; border: none; "
            "border-radius: 4px; padding: 6px 20px; font-weight: bold; }"
            "QPushButton:hover { background: #818cf8; }"
        )
        btn_row.addWidget(self._save_btn)

        root.addLayout(btn_row)
        root.addStretch()

    # ------------------------------------------------------------------
    # 値の読み込み / 書き込み
    # ------------------------------------------------------------------

    def _load_values(self) -> None:
        """現在の設定値をウィジェットに反映."""
        s = self.settings

        self._test_mode_cb.setChecked(s.test_mode)
        self._test_server_url.setText(s.test_server_url)
        self._base_url.setText(s.base_url)
        self._update_active_url()

        self._headless_cb.setChecked(s.browser.headless)
        self._timeout_ms.setValue(s.browser.timeout_ms)
        self._slow_mo.setValue(s.browser.slow_mo)

        self._max_images.setValue(s.post.max_images)
        self._image_max_kb.setValue(s.post.image_max_size_kb)

        self._timezone_label.setText(s.scheduler.timezone)
        self._max_retries.setValue(s.scheduler.max_retries)
        self._retry_interval.setValue(s.scheduler.retry_interval_sec)

    def _apply_values(self) -> None:
        """ウィジェットの値を設定オブジェクトに反映."""
        s = self.settings

        s.test_mode = self._test_mode_cb.isChecked()
        s.test_server_url = self._test_server_url.text()

        s.browser.headless = self._headless_cb.isChecked()
        s.browser.timeout_ms = self._timeout_ms.value()
        s.browser.slow_mo = self._slow_mo.value()

        s.post.max_images = self._max_images.value()
        s.post.image_max_size_kb = self._image_max_kb.value()

        s.scheduler.max_retries = self._max_retries.value()
        s.scheduler.retry_interval_sec = self._retry_interval.value()

    # ------------------------------------------------------------------
    # シグナル接続
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """シグナルを接続."""
        self._save_btn.clicked.connect(self._on_save)
        self._reset_btn.clicked.connect(self._on_reset)
        self._test_mode_cb.toggled.connect(self._update_active_url)

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        """設定を保存."""
        self._apply_values()
        try:
            self.settings.save()
            logger.info("設定を保存しました")
            self.settings_changed.emit()
        except OSError:
            logger.error("設定の保存に失敗しました")
            QMessageBox.critical(self, "エラー", "設定の保存に失敗しました。")

    def _on_reset(self) -> None:
        """デフォルト値にリセット."""
        reply = QMessageBox.question(
            self,
            "確認",
            "設定をデフォルトに戻しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            defaults = AppSettings()
            self.settings.test_mode = defaults.test_mode
            self.settings.test_server_url = defaults.test_server_url
            self.settings.browser = defaults.browser
            self.settings.post = defaults.post
            self.settings.scheduler = defaults.scheduler
            self._load_values()
            logger.info("設定をデフォルトにリセットしました")

    def _update_active_url(self) -> None:
        """アクティブURLラベルを更新."""
        if self._test_mode_cb.isChecked():
            url = self._test_server_url.text()
        else:
            url = self._base_url.text()
        self._active_url_label.setText(url)
