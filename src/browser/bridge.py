"""GUI↔ブラウザ非同期ブリッジ.

QThread上で独立したasyncioイベントループを駆動し、
GUIスレッドからのブラウザ操作リクエストをシグナル経由で中継する。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from PySide6.QtCore import QThread, Signal

from src.browser.auth import AuthManager
from src.browser.post import PostManager
from src.browser.session import SessionManager
from src.browser.story import StoryManager
from src.config.settings import AppSettings


class BrowserBridge(QThread):
    """GUI↔ブラウザ非同期ブリッジ.

    内部で専用の asyncio イベントループを保持し、
    Playwright 操作を非同期に実行する。
    結果は Qt シグナルで GUI スレッドへ通知する。
    """

    # ── シグナル定義 ──────────────────────────────────
    login_success = Signal()
    login_failed = Signal()
    post_success = Signal(str)
    post_failed = Signal(str)
    story_success = Signal()
    story_failed = Signal(str)
    status_changed = Signal(str)

    def __init__(
        self,
        settings: Optional[AppSettings] = None,
        parent: object = None,
    ) -> None:
        """ブリッジを初期化.

        Args:
            settings: アプリケーション設定。省略時はデフォルト値を使用。
            parent: 親 QObject。
        """
        super().__init__(parent)  # type: ignore[arg-type]
        self._settings = settings or AppSettings()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # マネージャー群（イベントループ起動後に利用）
        self._session = SessionManager(self._settings)
        self._auth = AuthManager(self._settings)
        self._post = PostManager(self._settings)
        self._story = StoryManager(self._settings)

    # ── QThread ライフサイクル ────────────────────────
    def run(self) -> None:
        """スレッドのエントリーポイント。asyncio ループを起動する."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        logger.info("BrowserBridge: イベントループ開始")
        try:
            self._loop.run_forever()
        finally:
            self._loop.run_until_complete(
                self._loop.shutdown_asyncgens(),
            )
            self._loop.close()
            self._loop = None
            logger.info("BrowserBridge: イベントループ終了")

    def stop(self) -> None:
        """イベントループを停止しスレッドを終了する."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.wait()

    # ── ヘルパー: GUI スレッドから安全にコルーチンを投入 ─
    def _submit(self, coro) -> None:  # noqa: ANN001
        """コルーチンをイベントループへ送信する.

        Args:
            coro: 実行する非同期コルーチン。
        """
        if self._loop is None or not self._loop.is_running():
            logger.warning("イベントループが起動していません")
            return
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    # ── 公開 API（GUI スレッドから呼び出す） ──────────

    def login(self) -> None:
        """ログイン処理を開始する."""
        self._submit(self._do_login())

    def create_post(
        self,
        text: str,
        image_paths: Optional[list[Path]] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> None:
        """投稿を作成する.

        Args:
            text: 投稿テキスト。
            image_paths: 添付画像パスのリスト。
            scheduled_at: 予約投稿日時。
        """
        self._submit(
            self._do_create_post(text, image_paths, scheduled_at),
        )

    def upload_story(
        self,
        image_path: Path,
        text: Optional[str] = None,
    ) -> None:
        """ストーリーをアップロードする.

        Args:
            image_path: ストーリー画像のパス。
            text: ストーリーテキスト。
        """
        self._submit(self._do_upload_story(image_path, text))

    # ── 内部非同期処理 ───────────────────────────────

    async def _ensure_context(self) -> None:
        """ブラウザコンテキストが起動済みか確認し、必要なら起動."""
        if self._session.context is None:
            self.status_changed.emit("ブラウザを起動中…")
            await self._session.start()
            self.status_changed.emit("ブラウザ起動完了")

    async def _do_login(self) -> None:
        """ログイン処理の実体."""
        try:
            self.status_changed.emit("ログイン処理を開始…")
            await self._ensure_context()
            context = self._session.context
            assert context is not None  # noqa: S101

            ok = await self._auth.ensure_logged_in(context)
            if ok:
                await self._session.save_session()
                self.status_changed.emit("ログイン成功")
                self.login_success.emit()
                logger.info("ログイン成功")
            else:
                self.status_changed.emit("ログイン失敗")
                self.login_failed.emit()
                logger.warning("ログイン失敗")
        except Exception as exc:
            logger.exception("ログイン中に例外が発生")
            self.status_changed.emit(f"ログインエラー: {exc}")
            self.login_failed.emit()

    async def _do_create_post(
        self,
        text: str,
        image_paths: Optional[list[Path]],
        scheduled_at: Optional[datetime],
    ) -> None:
        """投稿作成処理の実体."""
        try:
            self.status_changed.emit("投稿を作成中…")
            await self._ensure_context()
            context = self._session.context
            assert context is not None  # noqa: S101

            ok = await self._post.create_post(
                context, text, image_paths, scheduled_at,
            )
            if ok:
                msg = "投稿が完了しました"
                self.status_changed.emit(msg)
                self.post_success.emit(msg)
                logger.info(f"投稿成功: {text[:30]}…")
            else:
                msg = "投稿に失敗しました"
                self.status_changed.emit(msg)
                self.post_failed.emit(msg)
                logger.warning(f"投稿失敗: {text[:30]}…")
        except Exception as exc:
            err = f"投稿エラー: {exc}"
            logger.exception("投稿中に例外が発生")
            self.status_changed.emit(err)
            self.post_failed.emit(err)

    async def _do_upload_story(
        self,
        image_path: Path,
        text: Optional[str],
    ) -> None:
        """ストーリーアップロード処理の実体."""
        try:
            self.status_changed.emit("ストーリーをアップロード中…")
            await self._ensure_context()
            context = self._session.context
            assert context is not None  # noqa: S101

            ok = await self._story.upload_story(
                context, image_path, text,
            )
            if ok:
                self.status_changed.emit(
                    "ストーリーのアップロード完了",
                )
                self.story_success.emit()
                logger.info("ストーリーアップロード成功")
            else:
                msg = "ストーリーのアップロードに失敗しました"
                self.status_changed.emit(msg)
                self.story_failed.emit(msg)
                logger.warning("ストーリーアップロード失敗")
        except Exception as exc:
            err = f"ストーリーエラー: {exc}"
            logger.exception("ストーリーアップロード中に例外が発生")
            self.status_changed.emit(err)
            self.story_failed.emit(err)

    # ── リソース解放 ─────────────────────────────────

    async def _close_browser(self) -> None:
        """ブラウザリソースを解放する."""
        await self._session.close()
        logger.info("ブラウザリソースを解放")

    def shutdown(self) -> None:
        """ブラウザを閉じてスレッドを停止する."""
        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._close_browser(), self._loop,
            )
            future.result(timeout=15)
        self.stop()
