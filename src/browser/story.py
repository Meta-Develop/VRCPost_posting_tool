"""Story operations.

Automate VRCPost story features.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger
from playwright.async_api import BrowserContext

from src.config.settings import AppSettings


class StoryManager:
    """Story operation manager.

    Handles story uploads and updates.
    """

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    async def upload_story(
        self,
        context: BrowserContext,
        image_path: Path,
        text: Optional[str] = None,
    ) -> bool:
        """Upload a story.

        Args:
            context: Browser context.
            image_path: Path to the story image.
            text: Story text (optional).

        Returns:
            True on success.
        """
        page = await context.new_page()
        base_url = self.settings.active_url

        try:
            await page.goto(f"{base_url}/home", wait_until="networkidle")

            # Find the add-story button
            story_add_button = page.locator(
                "button:has-text('Story'), "
                "button:has-text('Story'), "
                "[data-testid='add-story'], "
                ".story-add-button"
            ).first
            await story_add_button.click()
            await page.wait_for_timeout(500)

            # Scope selectors to the modal/dialog
            modal = page.locator(
                "#story-modal, .modal:visible, "
                "[role='dialog']:visible"
            ).first

            # Image upload (file input inside the modal)
            file_input = modal.locator("input[type='file']").first
            await file_input.set_input_files(str(image_path))
            await page.wait_for_timeout(1500)
            logger.debug(f"Story image uploaded: {image_path.name}")

            # Text input (if provided)
            if text:
                text_input = modal.locator(
                    "input[type='text'], textarea"
                ).first
                await text_input.fill(text)

            # Submit button (inside the modal)
            submit_button = modal.locator(
                "button[type='submit'], "
                "button:has-text('Post'), "
                "button:has-text('Post'), "
                "button:has-text('Share')"
            ).first
            await submit_button.click()

            await page.wait_for_timeout(2000)
            logger.info(f"Story upload complete: {image_path.name}")
            return True

        except Exception as e:
            logger.error(f"Story upload failed: {e}")
            return False

        finally:
            await page.close()

    async def get_current_stories(self, context: BrowserContext) -> list[dict]:
        """Get the list of current stories.

        Args:
            context: Browser context.

        Returns:
            List of story information dicts.
        """
        page = await context.new_page()
        base_url = self.settings.active_url

        try:
            await page.goto(f"{base_url}/home", wait_until="networkidle")

            # Get story area information
            stories = []
            story_elements = page.locator(".story-item, [data-testid='story']")
            count = await story_elements.count()

            for i in range(count):
                el = story_elements.nth(i)
                story_info = {
                    "index": i,
                    "text": await el.inner_text(),
                }
                stories.append(story_info)

            logger.debug(f"Retrieved {len(stories)} stories")
            return stories

        except Exception as e:
            logger.error(f"Failed to get story list: {e}")
            return []

        finally:
            await page.close()
