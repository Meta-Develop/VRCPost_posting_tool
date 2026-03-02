"""認証・ログイン管理.

VRCPostへのログインフローを自動化する。
Google OAuth または メールアドレスでのログインに対応。
"""

from __future__ import annotations

from loguru import logger
from playwright.async_api import BrowserContext, Page

from src.config.settings import AppSettings


class AuthManager:
    """VRCPost認証管理.

    ログイン状態の確認、ログインフローの実行を行う。
    """

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    async def is_logged_in(self, page: Page) -> bool:
        """ログイン状態をチェック.

        Args:
            page: Playwrightページ

        Returns:
            ログイン済みならTrue
        """
        base_url = self.settings.active_url
        await page.goto(f"{base_url}/home", wait_until="networkidle")

        # ログインボタンが表示されているかで判定
        # VRCPostでは未ログインだとサインインボタンが表示される
        sign_in_button = page.locator("text=Sign in")
        guest_indicator = page.locator("text=Guest")

        is_guest = await guest_indicator.count() > 0
        has_sign_in = await sign_in_button.count() > 0

        if is_guest or has_sign_in:
            logger.info("未ログイン状態")
            return False

        logger.info("ログイン済み")
        return True

    async def login_interactive(self, context: BrowserContext) -> bool:
        """対話式ログイン.

        ブラウザを表示してユーザーに手動でログインしてもらう。
        ログイン完了を自動検出する。

        Args:
            context: ブラウザコンテキスト

        Returns:
            ログイン成功ならTrue
        """
        page = await context.new_page()
        base_url = self.settings.active_url

        try:
            await page.goto(f"{base_url}/home", wait_until="networkidle")

            # 既にログイン済みならそのまま返す
            if await self.is_logged_in(page):
                await page.close()
                return True

            logger.info("ログイン待機中... ブラウザでログインしてください")

            # ユーザーがログインするまで待機
            # ログイン後、ホーム画面にリダイレクトされることを期待
            # Guestテキストが消えたらログイン完了とみなす
            await page.wait_for_function(
                """() => {
                    const body = document.body.innerText;
                    return !body.includes('Guest') && !body.includes('Sign in to join');
                }""",
                timeout=300000,  # 5分待機
            )

            logger.info("ログイン成功を検出")
            await page.close()
            return True

        except Exception as e:
            logger.error(f"ログイン中にエラー: {e}")
            await page.close()
            return False

    async def ensure_logged_in(self, context: BrowserContext) -> bool:
        """ログイン状態を確認し、必要ならログインフローを実行.

        Args:
            context: ブラウザコンテキスト

        Returns:
            ログイン状態ならTrue
        """
        page = await context.new_page()
        try:
            if await self.is_logged_in(page):
                await page.close()
                return True
        finally:
            if not page.is_closed():
                await page.close()

        # ログインが必要
        return await self.login_interactive(context)
