"""セッション管理.

Playwrightのブラウザコンテキストを管理し、
認証状態の保持・復元を行う。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger
from playwright.async_api import (
    BrowserContext,
    Playwright,
    async_playwright,
)

from src.config.settings import AppSettings

SESSION_DIR = Path(__file__).parent.parent.parent / "config" / "browser_data"


class SessionManager:
    """ブラウザセッション管理.

    Playwrightのブラウザインスタンスとページの
    ライフサイクルを管理する。
    """

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._storage_path = SESSION_DIR / "storage_state.json"

    async def start(self) -> BrowserContext:
        """ブラウザコンテキストを起動.

        既存のセッション情報があれば復元する。

        Returns:
            BrowserContext
        """
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

        self._playwright = await async_playwright().start()

        browser_args = {
            "headless": self.settings.browser.headless,
            "slow_mo": self.settings.browser.slow_mo,
        }

        browser = await self._playwright.chromium.launch(**browser_args)

        # セッション復元
        context_args: dict = {
            "viewport": {"width": 1280, "height": 800},
            "locale": "ja-JP",
            "timezone_id": "Asia/Tokyo",
        }

        if self._storage_path.exists():
            context_args["storage_state"] = str(self._storage_path)
            logger.info("既存のセッションを復元")

        self._context = await browser.new_context(**context_args)
        logger.info("ブラウザコンテキストを起動")
        return self._context

    async def save_session(self) -> None:
        """現在のセッション状態を保存."""
        if self._context:
            await self._context.storage_state(path=str(self._storage_path))
            logger.info("セッションを保存")

    async def close(self) -> None:
        """ブラウザを終了."""
        if self._context:
            await self.save_session()
            await self._context.close()
            self._context = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("ブラウザを終了")

    @property
    def context(self) -> Optional[BrowserContext]:
        """現在のブラウザコンテキスト."""
        return self._context

    def has_session(self) -> bool:
        """保存済みセッションがあるか."""
        return self._storage_path.exists()

    def clear_session(self) -> None:
        """保存済みセッションを削除."""
        if self._storage_path.exists():
            self._storage_path.unlink()
            logger.info("セッションを削除")
