"""Thread-safe event system.

Queue-based communication between the GUI thread
and background threads.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable


class EventEmitter:
    """Thread-safe event emitter.

    Any thread can call emit() to enqueue events;
    the main thread calls process_pending() to dispatch handlers.
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[tuple[str, tuple[Any, ...]]] = queue.Queue()
        self._handlers: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()

    def on(self, event: str, handler: Callable) -> None:
        """Register an event handler."""
        with self._lock:
            self._handlers.setdefault(event, []).append(handler)

    def off(self, event: str, handler: Callable) -> None:
        """Unregister an event handler."""
        with self._lock:
            handlers = self._handlers.get(event, [])
            if handler in handlers:
                handlers.remove(handler)

    def emit(self, event: str, *args: Any) -> None:
        """Enqueue an event (thread-safe)."""
        self._queue.put((event, args))

    def process_pending(self) -> None:
        """Dispatch all queued events (call from the main thread)."""
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
