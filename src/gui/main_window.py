"""メインウィンドウ.

アプリケーションのエントリーポイントとメインウィンドウを定義する。
"""

from __future__ import annotations

import sys

from loguru import logger
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPushButton,
    QStatusBar,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.browser.bridge import BrowserBridge
from src.config.settings import AppSettings
from src.gui.log_tab import LogTab
from src.gui.post_tab import PostTab
from src.gui.schedule_tab import ScheduleTab
from src.gui.settings_tab import SettingsTab
from src.gui.story_tab import StoryTab
from src.scheduler.connector import SchedulerConnector
from src.scheduler.engine import SchedulerEngine
from src.utils.logger import setup_logger


class MainWindow(QMainWindow):
    """アプリケーションメインウィンドウ."""

    def __init__(self) -> None:
        super().__init__()

        # 設定読み込み
        self.settings = AppSettings.load()

        # ブラウザブリッジ起動
        self._bridge = BrowserBridge(self.settings, parent=self)
        self._bridge.start()

        # スケジューラー起動
        self._engine = SchedulerEngine(self.settings)
        self._connector = SchedulerConnector(
            self._engine, self._bridge, parent=self,
        )
        self._connector.start()

        self._setup_ui()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._setup_system_tray()
        self._connect_signals()

        logger.info("アプリケーション起動")

    def _setup_ui(self) -> None:
        """UIを構築."""
        self.setWindowTitle("VRCPost Posting Tool")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)

        # 中央ウィジェット
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # タブウィジェット
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 投稿タブ
        self.post_tab = PostTab(self.settings, self._bridge)
        self.tabs.addTab(self.post_tab, "投稿")

        # ストーリータブ
        self.story_tab = StoryTab(self.settings, self._bridge)
        self.tabs.addTab(self.story_tab, "ストーリー")

        # スケジュールタブ
        self.schedule_tab = ScheduleTab(self.settings, self._connector)
        self.tabs.addTab(self.schedule_tab, "スケジュール")

        # 設定タブ
        self.settings_tab = SettingsTab(self.settings)
        self.tabs.addTab(self.settings_tab, "設定")

        # ログタブ
        self.log_tab = LogTab()
        self.tabs.addTab(self.log_tab, "ログ")

    def _setup_menu_bar(self) -> None:
        """メニューバーを設定."""
        menu_bar: QMenuBar = self.menuBar()

        # ファイルメニュー
        file_menu = menu_bar.addMenu("ファイル")
        quit_action = file_menu.addAction("終了")
        quit_action.triggered.connect(self._quit_app)

        # アカウントメニュー
        account_menu = menu_bar.addMenu("アカウント")
        self._login_action = account_menu.addAction("ログイン")
        self._login_action.triggered.connect(self._on_login)

    def _setup_status_bar(self) -> None:
        """ステータスバーを設定."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        mode = "テストモード" if self.settings.test_mode else "本番モード"
        url = self.settings.active_url
        self._default_status = f"{mode} | {url}"
        self.status_bar.showMessage(self._default_status)

        # ステータスバーにログインボタンを配置
        self._login_btn = QPushButton("ログイン")
        self._login_btn.setFixedHeight(24)
        self._login_btn.setStyleSheet(
            "QPushButton { background: #6366f1; color: white; border: none; "
            "border-radius: 4px; padding: 2px 12px; font-size: 12px; }"
            "QPushButton:hover { background: #818cf8; }"
        )
        self._login_btn.clicked.connect(self._on_login)
        self.status_bar.addPermanentWidget(self._login_btn)

    def _setup_system_tray(self) -> None:
        """システムトレイアイコンを設定."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("VRCPost Posting Tool")

        # トレイメニュー
        tray_menu = QMenu()
        show_action = tray_menu.addAction("表示")
        show_action.triggered.connect(self.show)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("終了")
        quit_action.triggered.connect(QApplication.quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _connect_signals(self) -> None:
        """シグナルを接続する."""
        # ブリッジのステータス変更をステータスバーに反映
        self._bridge.status_changed.connect(self._on_status_changed)

        # ログイン結果
        self._bridge.login_success.connect(self._on_login_success)
        self._bridge.login_failed.connect(self._on_login_failed)

        # 投稿タブの予約シグナルをスケジュールタブに接続
        self.post_tab.post_scheduled.connect(self._on_job_scheduled)
        self.story_tab.story_scheduled.connect(self._on_job_scheduled)

    # ── スロット ─────────────────────────────────────

    def _on_status_changed(self, message: str) -> None:
        """ブリッジからのステータス変更を反映."""
        self.status_bar.showMessage(message, 5000)

    def _on_login(self) -> None:
        """ログインボタンクリック."""
        self._login_btn.setEnabled(False)
        self._login_btn.setText("ログイン中…")
        self._bridge.login()

    def _on_login_success(self) -> None:
        """ログイン成功."""
        self._login_btn.setText("ログイン済")
        self._login_btn.setEnabled(False)
        self.status_bar.showMessage(
            f"{self._default_status} | ログイン済",
        )
        logger.info("ログイン成功")

    def _on_login_failed(self) -> None:
        """ログイン失敗."""
        self._login_btn.setText("ログイン")
        self._login_btn.setEnabled(True)
        self.status_bar.showMessage("ログインに失敗しました", 5000)
        logger.warning("ログイン失敗")

    def _on_job_scheduled(self, job) -> None:
        """他タブからの予約ジョブを受け取る."""
        job_id = self._connector.add_job(job)
        self.schedule_tab.refresh_schedule()
        logger.info(f"ジョブ予約: {job_id}")

    def _quit_app(self) -> None:
        """アプリケーションを終了する."""
        # トレイアイコンを非表示にして完全に閉じる
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        QApplication.quit()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """トレイアイコンクリック."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()

    def closeEvent(self, event) -> None:
        """ウィンドウを閉じる際の処理."""
        # 設定を保存
        self.settings.save()

        # トレイに最小化するか終了するか
        if hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "VRCPost Posting Tool",
                "バックグラウンドで動作しています",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
            event.ignore()
        else:
            # リソース解放
            self.log_tab.cleanup()
            self._connector.stop()
            self._bridge.shutdown()
            logger.info("アプリケーション終了")
            event.accept()


def main() -> None:
    """アプリケーションエントリーポイント."""
    setup_logger()

    app = QApplication(sys.argv)
    app.setApplicationName("VRCPost Posting Tool")
    app.setOrganizationName("Meta-Develop")

    # ダークテーマ
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
