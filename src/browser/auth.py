"""Authentication and login management.

Automate VRCPost login flows.
Supports Google OAuth and email-based login.
"""

from __future__ import annotations

from loguru import logger
from playwright.async_api import BrowserContext, Page

from src.config.settings import AppSettings


class AuthManager:
    """VRCPost authentication manager.

    Checks login status and executes login flows.
    """

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    async def is_logged_in(self, page: Page) -> bool:
        """Check whether the user is logged in.

        Args:
            page: Playwright page.

        Returns:
            True if already logged in.
        """
        base_url = self.settings.active_url
        await page.goto(f"{base_url}/home", wait_until="networkidle")

        # Determine login state by checking for sign-in / guest indicators
        sign_in_button = page.locator("text=Sign in")
        guest_indicator = page.locator("text=Guest")

        is_guest = await guest_indicator.count() > 0
        has_sign_in = await sign_in_button.count() > 0

        if is_guest or has_sign_in:
            logger.info("Not logged in")
            return False

        logger.info("Logged in")
        return True

    async def login_interactive(self, context: BrowserContext) -> bool:
        """Interactive login.

        Show the browser so the user can log in manually.
        Login completion is detected automatically.

        Args:
            context: Browser context.

        Returns:
            True on successful login.
        """
        page = await context.new_page()
        base_url = self.settings.active_url

        try:
            await page.goto(f"{base_url}/home", wait_until="networkidle")

            # Already logged in — return immediately
            if await self.is_logged_in(page):
                await page.close()
                return True

            logger.info("Waiting for login... please log in via the browser")

            # Wait until the user completes login
            # Expect a redirect to the home screen after login
            # Treat disappearance of 'Guest' text as login completion
            await page.wait_for_function(
                """() => {
                    const body = document.body.innerText;
                    return !body.includes('Guest') && !body.includes('Sign in to join');
                }""",
                timeout=300000,  # 5 min
            )

            logger.info("Login success detected")
            await page.close()
            return True

        except Exception as e:
            logger.error(f"Error during login: {e}")
            await page.close()
            return False

    async def ensure_logged_in(self, context: BrowserContext) -> bool:
        """Ensure the user is logged in, running the login flow if necessary.

        Args:
            context: Browser context.

        Returns:
            True if logged in.
        """
        page = await context.new_page()
        try:
            if await self.is_logged_in(page):
                await page.close()
                return True
        finally:
            if not page.is_closed():
                await page.close()

        # Login required
        return await self.login_interactive(context)
