"""デスクトップ通知マネージャ.

QSystemTrayIcon を介した通知と、画像残数の監視を行う。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QSystemTrayIcon

from src.utils.image_history import ImageHistory


class NotificationManager(QObject):
    """アプリ内通知を一元管理するマネージャ.

    - 投稿成功/失敗の通知
    - スケジュール実行通知
    - 未使用画像の残数が閾値を下回った際の警告
    """

    # 画像不足を GUI に通知するシグナル
    low_image_warning = Signal(str, int, int)  # dir_path, remaining, threshold

    def __init__(
        self,
        tray_icon: QSystemTrayIcon | None = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._tray = tray_icon
        self._history = ImageHistory()

        # 監視対象ディレクトリと閾値
        self._watch_dirs: dict[str, int] = {}  # dir_path -> threshold
        self._already_warned: set[str] = set()  # 二重通知防止

        # 画像残数チェックタイマー (5分ごと)
        self._watch_timer = QTimer(self)
        self._watch_timer.timeout.connect(self._check_image_levels)
        self._watch_timer.start(300_000)

    # ── トレイ通知 ────────────────────────────────────

    def notify(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        duration_ms: int = 3000,
    ) -> None:
        """デスクトップ通知を表示する.

        Args:
            title: 通知タイトル
            message: 通知メッセージ
            icon: アイコン種別
            duration_ms: 表示時間 (ms)
        """
        if self._tray and self._tray.isVisible():
            self._tray.showMessage(title, message, icon, duration_ms)
        logger.info(f"通知: [{title}] {message}")

    def notify_success(self, message: str) -> None:
        """成功通知."""
        self.notify("投稿成功", message, QSystemTrayIcon.MessageIcon.Information)

    def notify_error(self, message: str) -> None:
        """エラー通知."""
        self.notify("エラー", message, QSystemTrayIcon.MessageIcon.Critical, 5000)

    def notify_schedule(self, message: str) -> None:
        """スケジュール実行通知."""
        self.notify("スケジュール実行", message, QSystemTrayIcon.MessageIcon.Information)

    def notify_warning(self, message: str) -> None:
        """警告通知."""
        self.notify("警告", message, QSystemTrayIcon.MessageIcon.Warning, 5000)

    # ── 画像残数監視 ──────────────────────────────────

    def watch_directory(self, directory: str | Path, threshold: int = 5) -> None:
        """ディレクトリの未使用画像数を監視対象に追加.

        Args:
            directory: 監視するディレクトリパス
            threshold: この枚数以下になったら警告
        """
        dir_str = str(Path(directory).resolve())
        self._watch_dirs[dir_str] = threshold
        self._already_warned.discard(dir_str)
        logger.info(f"画像監視追加: {dir_str} (閾値: {threshold}枚)")
        # 即時チェック
        self._check_single_dir(dir_str, threshold)

    def unwatch_directory(self, directory: str | Path) -> None:
        """ディレクトリの監視を解除."""
        dir_str = str(Path(directory).resolve())
        self._watch_dirs.pop(dir_str, None)
        self._already_warned.discard(dir_str)

    def _check_image_levels(self) -> None:
        """全監視ディレクトリの画像残数をチェック."""
        for dir_str, threshold in list(self._watch_dirs.items()):
            self._check_single_dir(dir_str, threshold)

    def _check_single_dir(self, dir_str: str, threshold: int) -> None:
        """1ディレクトリの画像残数チェック."""
        directory = Path(dir_str)
        if not directory.is_dir():
            return

        total, used, remaining = self._history.get_stats(directory)
        if total == 0:
            return

        if remaining <= threshold and dir_str not in self._already_warned:
            self._already_warned.add(dir_str)
            folder_name = directory.name
            msg = (
                f"「{folder_name}」の未使用画像が残り {remaining} 枚です。\n"
                f"(全{total}枚中 {used}枚 使用済み)"
            )
            self.notify_warning(msg)
            self.low_image_warning.emit(dir_str, remaining, threshold)
            logger.warning(f"画像残数警告: {folder_name} 残り{remaining}枚")
        elif remaining > threshold:
            # 閾値超えたら警告フラグをリセット (リセット後にまた下回れば再通知)
            self._already_warned.discard(dir_str)

    def set_tray_icon(self, tray_icon: QSystemTrayIcon) -> None:
        """トレイアイコンを後から設定する."""
        self._tray = tray_icon

    def cleanup(self) -> None:
        """リソース解放."""
        self._watch_timer.stop()
