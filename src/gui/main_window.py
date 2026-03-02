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
    QStatusBar,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import AppSettings
from src.gui.post_tab import PostTab
from src.gui.schedule_tab import ScheduleTab
from src.gui.story_tab import StoryTab
from src.utils.logger import setup_logger


class MainWindow(QMainWindow):
    """アプリケーションメインウィンドウ."""

    def __init__(self) -> None:
        super().__init__()

        # 設定読み込み
        self.settings = AppSettings.load()

        self._setup_ui()
        self._setup_status_bar()
        self._setup_system_tray()

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
        self.post_tab = PostTab(self.settings)
        self.tabs.addTab(self.post_tab, "投稿")

        # ストーリータブ
        self.story_tab = StoryTab(self.settings)
        self.tabs.addTab(self.story_tab, "ストーリー")

        # スケジュールタブ
        self.schedule_tab = ScheduleTab(self.settings)
        self.tabs.addTab(self.schedule_tab, "スケジュール")

    def _setup_status_bar(self) -> None:
        """ステータスバーを設定."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        mode = "テストモード" if self.settings.test_mode else "本番モード"
        url = self.settings.active_url
        self.status_bar.showMessage(f"{mode} | {url}")

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
