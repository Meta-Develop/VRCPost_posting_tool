"""投稿操作.

VRCPostへのテキスト・画像投稿を自動化する。
予約投稿機能にも対応。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from playwright.async_api import BrowserContext, Page

from src.config.settings import AppSettings


class PostManager:
    """投稿操作管理.

    テキスト投稿、画像付き投稿、予約投稿を行う。
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
        """投稿を作成.

        Args:
            context: ブラウザコンテキスト
            text: 投稿テキスト
            image_paths: 添付画像パスのリスト
            scheduled_at: 予約投稿日時（Noneなら即時投稿）

        Returns:
            投稿成功ならTrue
        """
        page = await context.new_page()
        base_url = self.settings.active_url

        try:
            await page.goto(f"{base_url}/home", wait_until="networkidle")

            # テキスト入力エリアを探してクリック
            text_area = page.locator("textarea, [contenteditable='true'], [role='textbox']").first
            await text_area.click()
            await text_area.fill(text)
            logger.debug(f"テキスト入力: {text[:50]}...")

            # 画像アップロード
            if image_paths:
                for img_path in image_paths:
                    await self._upload_image(page, img_path)

            # 予約投稿の設定
            if scheduled_at:
                await self._set_schedule(page, scheduled_at)

            # 投稿ボタンをクリック
            post_button = page.locator(
                "button:has-text('Post'), button:has-text('投稿'), "
                "button[type='submit']:has-text('Post')"
            ).first
            await post_button.click()

            # 投稿完了を待つ
            await page.wait_for_timeout(2000)

            logger.info(
                f"投稿{'予約' if scheduled_at else ''}完了: {text[:30]}..."
            )
            return True

        except Exception as e:
            logger.error(f"投稿に失敗: {e}")
            return False

        finally:
            await page.close()

    async def _upload_image(self, page: Page, image_path: Path) -> None:
        """画像をアップロード.

        Args:
            page: Playwrightページ
            image_path: アップロードする画像のパス
        """
        # ファイル入力要素を探す
        file_input = page.locator("input[type='file']").first

        # 非表示でも操作できるようにset_input_filesを使用
        await file_input.set_input_files(str(image_path))

        # アップロード完了を待つ
        await page.wait_for_timeout(1000)
        logger.debug(f"画像アップロード: {image_path.name}")

    async def _set_schedule(self, page: Page, scheduled_at: datetime) -> None:
        """予約投稿日時を設定.

        VRCPostの予約投稿UIを操作して日時を設定する。

        Args:
            page: Playwrightページ
            scheduled_at: 予約日時
        """
        # 予約投稿ボタン/オプションを探してクリック
        schedule_button = page.locator(
            "button:has-text('予約'), button:has-text('Schedule'), "
            "[data-testid='schedule-button']"
        ).first
        await schedule_button.click()
        await page.wait_for_timeout(500)

        # 日時入力
        date_input = page.locator("input[type='date'], input[type='datetime-local']").first
        await date_input.fill(scheduled_at.strftime("%Y-%m-%dT%H:%M"))

        logger.debug(f"予約日時設定: {scheduled_at.isoformat()}")

    async def delete_post(self, context: BrowserContext, post_id: str) -> bool:
        """投稿を削除.

        Args:
            context: ブラウザコンテキスト
            post_id: 削除対象の投稿ID

        Returns:
            削除成功ならTrue
        """
        page = await context.new_page()
        base_url = self.settings.active_url

        try:
            await page.goto(f"{base_url}/post/{post_id}", wait_until="networkidle")

            # 削除メニューを開く
            menu_button = page.locator("[aria-label='more'], button:has-text('...')").first
            await menu_button.click()

            # 削除ボタンをクリック
            delete_button = page.locator(
                "button:has-text('削除'), button:has-text('Delete')"
            ).first
            await delete_button.click()

            # 確認ダイアログ
            confirm_button = page.locator(
                "button:has-text('確認'), button:has-text('OK'), button:has-text('Confirm')"
            ).first
            await confirm_button.click()

            await page.wait_for_timeout(1000)
            logger.info(f"投稿削除: {post_id}")
            return True

        except Exception as e:
            logger.error(f"投稿削除に失敗: {e}")
            return False

        finally:
            await page.close()
