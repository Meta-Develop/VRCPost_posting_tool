"""Session management.

Manage Playwright browser contexts and
persist/restore authentication state.
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
    """Browser session manager.

    Manages the lifecycle of Playwright browser instances and pages.
    """

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._storage_path = SESSION_DIR / "storage_state.json"

    async def start(self) -> BrowserContext:
        """Start a browser context.

        Restores existing session data if available.

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

        # Session restore
        context_args: dict = {
            "viewport": {"width": 1280, "height": 800},
            "locale": "ja-JP",
            "timezone_id": "Asia/Tokyo",
        }

        if self._storage_path.exists():
            context_args["storage_state"] = str(self._storage_path)
            logger.info("Restoring existing session")

        self._context = await browser.new_context(**context_args)
        logger.info("Browser context started")
        return self._context

    async def save_session(self) -> None:
        """Save the current session state."""
        if self._context:
            await self._context.storage_state(path=str(self._storage_path))
            logger.info("Session saved")

    async def close(self) -> None:
        """Close the browser."""
        if self._context:
            await self.save_session()
            await self._context.close()
            self._context = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser closed")

    @property
    def context(self) -> Optional[BrowserContext]:
        """Current browser context."""
        return self._context

    def has_session(self) -> bool:
        """Check if a saved session exists."""
        return self._storage_path.exists()

    def clear_session(self) -> None:
        """Delete the saved session."""
        if self._storage_path.exists():
            self._storage_path.unlink()
            logger.info("Session deleted")
