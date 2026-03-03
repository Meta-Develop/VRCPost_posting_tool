"""通知ユーティリティ.

アプリ内トースト通知を EventEmitter 経由で発行する。
メインウィンドウ側でトースト UI を表示する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from src.gui.events import EventEmitter


class NotificationManager:
    """通知マネージャ.

    Events:
        notification (str, str, str): (title, message, level)
            level は "info" | "warning" | "error"
    """

    def __init__(self, emitter: EventEmitter) -> None:
        self.emitter = emitter

    def info(self, title: str, message: str) -> None:
        logger.info(f"[通知] {title}: {message}")
        self.emitter.emit("notification", title, message, "info")

    def warning(self, title: str, message: str) -> None:
        logger.warning(f"[通知] {title}: {message}")
        self.emitter.emit("notification", title, message, "warning")

    def error(self, title: str, message: str) -> None:
        logger.error(f"[通知] {title}: {message}")
        self.emitter.emit("notification", title, message, "error")
