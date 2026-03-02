"""ストーリー操作.

VRCPostのストーリー機能を自動化する。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger
from playwright.async_api import BrowserContext

from src.config.settings import AppSettings


class StoryManager:
    """ストーリー操作管理.

    ストーリーのアップロード・更新を行う。
    """

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    async def upload_story(
        self,
        context: BrowserContext,
        image_path: Path,
        text: Optional[str] = None,
    ) -> bool:
        """ストーリーをアップロード.

        Args:
            context: ブラウザコンテキスト
            image_path: ストーリー画像のパス
            text: ストーリーテキスト（任意）

        Returns:
            アップロード成功ならTrue
        """
        page = await context.new_page()
        base_url = self.settings.active_url

        try:
            await page.goto(f"{base_url}/home", wait_until="networkidle")

            # ストーリー追加ボタンを探す
            # VRCPostのストーリーUIに合わせてセレクタを調整
            story_add_button = page.locator(
                "button:has-text('ストーリー'), "
                "button:has-text('Story'), "
                "[data-testid='add-story'], "
                ".story-add-button"
            ).first
            await story_add_button.click()
            await page.wait_for_timeout(500)

            # 画像アップロード
            file_input = page.locator("input[type='file']").first
            await file_input.set_input_files(str(image_path))
            await page.wait_for_timeout(1500)
            logger.debug(f"ストーリー画像アップロード: {image_path.name}")

            # テキスト入力（あれば）
            if text:
                text_input = page.locator(
                    "textarea, [contenteditable='true'], input[type='text']"
                ).first
                await text_input.fill(text)

            # 投稿ボタン
            submit_button = page.locator(
                "button:has-text('投稿'), button:has-text('Post'), "
                "button:has-text('Share'), button[type='submit']"
            ).first
            await submit_button.click()

            await page.wait_for_timeout(2000)
            logger.info(f"ストーリーアップロード完了: {image_path.name}")
            return True

        except Exception as e:
            logger.error(f"ストーリーアップロードに失敗: {e}")
            return False

        finally:
            await page.close()

    async def get_current_stories(self, context: BrowserContext) -> list[dict]:
        """現在のストーリー一覧を取得.

        Args:
            context: ブラウザコンテキスト

        Returns:
            ストーリー情報のリスト
        """
        page = await context.new_page()
        base_url = self.settings.active_url

        try:
            await page.goto(f"{base_url}/home", wait_until="networkidle")

            # ストーリーエリアの情報を取得
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

            logger.debug(f"ストーリー {len(stories)}件 取得")
            return stories

        except Exception as e:
            logger.error(f"ストーリー一覧の取得に失敗: {e}")
            return []

        finally:
            await page.close()
