"""スレッドセーフなイベントシステム.

GUIスレッドとバックグラウンドスレッド間の通信を
キューベースで安全に行う。
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable


class EventEmitter:
    """スレッドセーフなイベントエミッター.

    任意のスレッドから emit() でイベントをキューに投入し、
    メインスレッドで process_pending() を呼んでハンドラを実行する。
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[tuple[str, tuple[Any, ...]]] = queue.Queue()
        self._handlers: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()

    def on(self, event: str, handler: Callable) -> None:
        """イベントハンドラを登録."""
        with self._lock:
            self._handlers.setdefault(event, []).append(handler)

    def off(self, event: str, handler: Callable) -> None:
        """イベントハンドラを解除."""
        with self._lock:
            handlers = self._handlers.get(event, [])
            if handler in handlers:
                handlers.remove(handler)

    def emit(self, event: str, *args: Any) -> None:
        """イベントをキューに投入 (スレッドセーフ)."""
        self._queue.put((event, args))

    def process_pending(self) -> None:
        """キュー内の全イベントをディスパッチ (メインスレッドから呼ぶ)."""
        while True:
            try:
                event, args = self._queue.get_nowait()
            except queue.Empty:
                break
            with self._lock:
                handlers = list(self._handlers.get(event, []))
            for handler in handlers:
                try:
                    handler(*args)
                except Exception:
                    pass
