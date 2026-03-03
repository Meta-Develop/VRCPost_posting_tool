"""ブラウザ操作ブリッジ.

GUIスレッドからブラウザ操作を安全に実行するための
スレッドベースブリッジ。
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
    """ブラウザ操作ブリッジ.

    専用スレッドで asyncio イベントループを駆動し、
    Playwright 操作を非同期実行する。
    結果は EventEmitter 経由で GUI スレッドに通知する。

    Events:
        login_success  : ログイン成功
        login_failed   : ログイン失敗
        post_success   : 投稿成功 (str: メッセージ)
        post_failed    : 投稿失敗 (str: エラー)
        story_success  : ストーリー成功
        story_failed   : ストーリー失敗 (str: エラー)
        status_changed : 状態テキスト変更 (str)
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

    # ── スレッド制御 ────────────────────────────────

    def run(self) -> None:
        """スレッドのメインルーチン (asyncio ループ駆動)."""
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
        """マネージャー群を初期化."""
        self._session = SessionManager(self.settings)
        self._auth = AuthManager(self.settings)
        self._post = PostManager(self.settings)
        self._story = StoryManager(self.settings)

        ctx = await self._session.start()
        self.emitter.emit("status_changed", "ブラウザ起動完了")
        logger.info(f"BrowserBridge 起動 (context={ctx is not None})")

    async def _teardown(self) -> None:
        """リソース解放."""
        if self._session:
            await self._session.close()
        logger.info("BrowserBridge 停止")

    def shutdown(self) -> None:
        """ブリッジを安全に停止."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
            self.join(timeout=10)

    # ── パブリック API (GUI スレッドから呼ぶ) ──────────

    def login(self) -> None:
        """ログインを開始."""
        self._submit(self._do_login())

    def create_post(
        self,
        text: str,
        image_paths: Optional[list[str]] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> None:
        """投稿を作成."""
        paths = [Path(p) for p in image_paths] if image_paths else None
        self._submit(self._do_post(text, paths, scheduled_at))

    def upload_story(
        self,
        image_path: str,
        text: Optional[str] = None,
    ) -> None:
        """ストーリーをアップロード."""
        self._submit(self._do_story(Path(image_path), text))

    # ── 非同期タスク ──────────────────────────────────

    async def _do_login(self) -> None:
        self.emitter.emit("status_changed", "ログイン中...")
        try:
            assert self._session and self._auth
            ctx = self._session.context
            assert ctx
            ok = await self._auth.ensure_logged_in(ctx)
            if ok:
                await self._session.save_session()
                self.emitter.emit("login_success")
                self.emitter.emit("status_changed", "ログイン済み")
            else:
                self.emitter.emit("login_failed")
                self.emitter.emit("status_changed", "ログイン失敗")
        except Exception as exc:
            logger.error(f"ログインエラー: {exc}")
            self.emitter.emit("login_failed")
            self.emitter.emit("status_changed", f"ログインエラー: {exc}")

    async def _do_post(
        self,
        text: str,
        image_paths: Optional[list[Path]],
        scheduled_at: Optional[datetime],
    ) -> None:
        self.emitter.emit("status_changed", "投稿中...")
        try:
            assert self._session and self._post
            ctx = self._session.context
            assert ctx
            ok = await self._post.create_post(ctx, text, image_paths, scheduled_at)
            if ok:
                self.emitter.emit("post_success", f"投稿完了: {text[:30]}")
                self.emitter.emit("status_changed", "投稿完了")
            else:
                self.emitter.emit("post_failed", "投稿に失敗しました")
                self.emitter.emit("status_changed", "投稿失敗")
        except Exception as exc:
            logger.error(f"投稿エラー: {exc}")
            self.emitter.emit("post_failed", str(exc))
            self.emitter.emit("status_changed", f"投稿エラー: {exc}")

    async def _do_story(self, image_path: Path, text: Optional[str]) -> None:
        self.emitter.emit("status_changed", "ストーリーアップロード中...")
        try:
            assert self._session and self._story
            ctx = self._session.context
            assert ctx
            ok = await self._story.upload_story(ctx, image_path, text)
            if ok:
                self.emitter.emit("story_success")
                self.emitter.emit("status_changed", "ストーリー完了")
            else:
                self.emitter.emit("story_failed", "ストーリー失敗")
                self.emitter.emit("status_changed", "ストーリー失敗")
        except Exception as exc:
            logger.error(f"ストーリーエラー: {exc}")
            self.emitter.emit("story_failed", str(exc))
            self.emitter.emit("status_changed", f"ストーリーエラー: {exc}")

    # ── ヘルパー ──────────────────────────────────────

    def _submit(self, coro: object) -> None:
        """コルーチンをイベントループに投入."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self._loop)  # type: ignore[arg-type]
        else:
            logger.warning("Bridge loop is not running — cannot submit task")
