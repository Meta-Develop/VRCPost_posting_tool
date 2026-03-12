"""Notification utilities.

Emits in-app toast notifications via EventEmitter.
The main window renders the toast UI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from src.gui.events import EventEmitter


class NotificationManager:
    """Notification manager.

    Events:
        notification (str, str, str): (title, message, level)
            level is "info" | "warning" | "error"
    """

    def __init__(self, emitter: EventEmitter) -> None:
        self.emitter = emitter

    def info(self, title: str, message: str) -> None:
        logger.info(f"[Notification] {title}: {message}")
        self.emitter.emit("notification", title, message, "info")

    def warning(self, title: str, message: str) -> None:
        logger.warning(f"[Notification] {title}: {message}")
        self.emitter.emit("notification", title, message, "warning")

    def error(self, title: str, message: str) -> None:
        logger.error(f"[Notification] {title}: {message}")
        self.emitter.emit("notification", title, message, "error")
