"""Browser operation bridge.

Thread-based bridge for safely executing browser operations
from the GUI thread.
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from loguru import logger

from src.browser.auth import AuthManager
from src.browser.post import PostManager
from src.browser.session import SessionManager
from src.browser.story import StoryManager

if TYPE_CHECKING:
    from datetime import datetime

    from src.config.settings import AppSettings
    from src.gui.events import EventEmitter


class BrowserBridge(threading.Thread):
    """Browser operation bridge.

    Drives an asyncio event loop in a dedicated thread and
    executes Playwright operations asynchronously.
    Results are reported to the GUI thread via EventEmitter.

    Events:
        login_success  : Login succeeded
        login_failed   : Login failed
        post_success   : Post succeeded (str: message)
        post_failed    : Post failed (str: error)
        story_success  : Story succeeded
        story_failed   : Story failed (str: error)
        status_changed : Status text changed (str)
    """

    def __init__(self, settings: AppSettings, emitter: EventEmitter) -> None:
        super().__init__(daemon=True)
        self.settings = settings
        self.emitter = emitter
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._session: Optional[SessionManager] = None
        self._auth: Optional[AuthManager] = None
        self._post: Optional[PostManager] = None
        self._story: Optional[StoryManager] = None

    # ── Thread control ─────────────────────────────

    def run(self) -> None:
        """Thread main routine (asyncio loop driver)."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._setup())
            self._loop.run_forever()
        except Exception as exc:
            logger.error(f"Bridge loop error: {exc}")
        finally:
            self._loop.run_until_complete(self._teardown())
            self._loop.close()

    async def _setup(self) -> None:
        """Initialize managers."""
        self._session = SessionManager(self.settings)
        self._auth = AuthManager(self.settings)
        self._post = PostManager(self.settings)
        self._story = StoryManager(self.settings)

        ctx = await self._session.start()
        self.emitter.emit("status_changed", "Browser started")
        logger.info(f"BrowserBridge started (context={ctx is not None})")

    async def _teardown(self) -> None:
        """Release resources."""
        if self._session:
            await self._session.close()
        logger.info("BrowserBridge stopped")

    def shutdown(self) -> None:
        """Shut down the bridge safely."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
            self.join(timeout=10)

    # ── Public API (called from GUI thread) ────────

    def login(self) -> None:
        """Start login."""
        self._submit(self._do_login())

    def create_post(
        self,
        text: str,
        image_paths: Optional[list[str]] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> None:
        """Create a post."""
        paths = [Path(p) for p in image_paths] if image_paths else None
        self._submit(self._do_post(text, paths, scheduled_at))

    def upload_story(
        self,
        image_path: str,
        text: Optional[str] = None,
    ) -> None:
        """Upload a story."""
        self._submit(self._do_story(Path(image_path), text))

    # ── Async tasks ────────────────────────────────

    async def _do_login(self) -> None:
        self.emitter.emit("status_changed", "Logging in...")
        try:
            assert self._session and self._auth
            ctx = self._session.context
            assert ctx
            ok = await self._auth.ensure_logged_in(ctx)
            if ok:
                await self._session.save_session()
                self.emitter.emit("login_success")
                self.emitter.emit("status_changed", "Logged in")
            else:
                self.emitter.emit("login_failed")
                self.emitter.emit("status_changed", "Login failed")
        except Exception as exc:
            logger.error(f"Login error: {exc}")
            self.emitter.emit("login_failed")
            self.emitter.emit("status_changed", f"Login error: {exc}")

    async def _do_post(
        self,
        text: str,
        image_paths: Optional[list[Path]],
        scheduled_at: Optional[datetime],
    ) -> None:
        self.emitter.emit("status_changed", "Posting...")
        try:
            assert self._session and self._post
            ctx = self._session.context
            assert ctx
            ok = await self._post.create_post(ctx, text, image_paths, scheduled_at)
            if ok:
                self.emitter.emit("post_success", f"Post complete: {text[:30]}")
                self.emitter.emit("status_changed", "Post complete")
            else:
                self.emitter.emit("post_failed", "Post failed")
                self.emitter.emit("status_changed", "Post failed")
        except Exception as exc:
            logger.error(f"Post error: {exc}")
            self.emitter.emit("post_failed", str(exc))
            self.emitter.emit("status_changed", f"Post error: {exc}")

    async def _do_story(self, image_path: Path, text: Optional[str]) -> None:
        self.emitter.emit("status_changed", "Uploading story...")
        try:
            assert self._session and self._story
            ctx = self._session.context
            assert ctx
            ok = await self._story.upload_story(ctx, image_path, text)
            if ok:
                self.emitter.emit("story_success")
                self.emitter.emit("status_changed", "Story complete")
            else:
                self.emitter.emit("story_failed", "Story failed")
                self.emitter.emit("status_changed", "Story failed")
        except Exception as exc:
            logger.error(f"Story error: {exc}")
            self.emitter.emit("story_failed", str(exc))
            self.emitter.emit("status_changed", f"Story error: {exc}")

    # ── Helpers ─────────────────────────────────────

    def _submit(self, coro: object) -> None:
        """Submit a coroutine to the event loop."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self._loop)  # type: ignore[arg-type]
        else:
            logger.warning("Bridge loop is not running — cannot submit task")
