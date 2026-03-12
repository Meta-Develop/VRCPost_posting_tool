"""Post operations.

Automate text and image posting on VRCPost.
Supports scheduled posting.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from playwright.async_api import BrowserContext, Page

from src.config.settings import AppSettings


class PostManager:
    """Post operation manager.

    Handles text posts, image-attached posts, and scheduled posts.
    """

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    async def create_post(
        self,
        context: BrowserContext,
        text: str,
        image_paths: Optional[list[Path]] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> bool:
        """Create a post.

        Args:
            context: Browser context.
            text: Post text.
            image_paths: List of image file paths to attach.
            scheduled_at: Scheduled post time (None for immediate).

        Returns:
            True on success.
        """
        page = await context.new_page()
        base_url = self.settings.active_url

        try:
            await page.goto(f"{base_url}/home", wait_until="networkidle")

            # Find and click the text input area
            text_area = page.locator("textarea, [contenteditable='true'], [role='textbox']").first
            await text_area.click()
            await text_area.fill(text)
            logger.debug(f"Text entered: {text[:50]}...")

            # Upload images
            if image_paths:
                for img_path in image_paths:
                    await self._upload_image(page, img_path)

            # Set scheduled post time
            if scheduled_at:
                await self._set_schedule(page, scheduled_at)

            # Click the post button
            post_button = page.locator(
                "button:has-text('Post'), button:has-text('Post'), "
                "button[type='submit']:has-text('Post')"
            ).first
            await post_button.click()

            # Wait for post completion
            await page.wait_for_timeout(2000)

            logger.info(
                f"Post{' scheduled' if scheduled_at else ''} complete: {text[:30]}..."
            )
            return True

        except Exception as e:
            logger.error(f"Post failed: {e}")
            return False

        finally:
            await page.close()

    async def _upload_image(self, page: Page, image_path: Path) -> None:
        """Upload an image.

        Args:
            page: Playwright page.
            image_path: Path to the image file to upload.
        """
        # Find the file input element
        file_input = page.locator("input[type='file']").first

        # Use set_input_files to work even with hidden inputs
        await file_input.set_input_files(str(image_path))

        # Wait for upload to complete
        await page.wait_for_timeout(1000)
        logger.debug(f"Image uploaded: {image_path.name}")

    async def _set_schedule(self, page: Page, scheduled_at: datetime) -> None:
        """Set the scheduled post date/time.

        Operates VRCPost's schedule UI to set the date and time.

        Args:
            page: Playwright page.
            scheduled_at: Scheduled date/time.
        """
        # Find and click the schedule button/option
        schedule_button = page.locator(
            "button:has-text('Schedule'), button:has-text('Schedule'), "
            "[data-testid='schedule-button']"
        ).first
        await schedule_button.click()
        await page.wait_for_timeout(500)

        # Date/time input
        date_input = page.locator("input[type='date'], input[type='datetime-local']").first
        await date_input.fill(scheduled_at.strftime("%Y-%m-%dT%H:%M"))

        logger.debug(f"Schedule set: {scheduled_at.isoformat()}")

    async def delete_post(self, context: BrowserContext, post_id: str) -> bool:
        """Delete a post.

        Args:
            context: Browser context.
            post_id: ID of the post to delete.

        Returns:
            True on success.
        """
        page = await context.new_page()
        base_url = self.settings.active_url

        try:
            await page.goto(f"{base_url}/post/{post_id}", wait_until="networkidle")

            # Open the more menu
            menu_button = page.locator("[aria-label='more'], button:has-text('...')").first
            await menu_button.click()

            # Click delete
            delete_button = page.locator(
                "button:has-text('Delete'), button:has-text('Delete')"
            ).first
            await delete_button.click()

            # Confirm dialog
            confirm_button = page.locator(
                "button:has-text('OK'), button:has-text('Confirm')"
            ).first
            await confirm_button.click()

            await page.wait_for_timeout(1000)
            logger.info(f"Post deleted: {post_id}")
            return True

        except Exception as e:
            logger.error(f"Post deletion failed: {e}")
            return False

        finally:
            await page.close()
