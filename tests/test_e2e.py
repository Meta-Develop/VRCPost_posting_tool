"""E2Eテスト.

ローカルテストサーバーに対してPlaywrightで
フルフローのE2Eテストを実行する。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from loguru import logger
from PIL import Image
from playwright.async_api import BrowserContext, Page, async_playwright

BASE_URL = "http://localhost:5000"


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _create_test_image(directory: Path, name: str = "test.png") -> Path:
    """テスト用の100×100赤色PNGを生成して返す."""
    path = directory / name
    img = Image.new("RGB", (100, 100), color="red")
    img.save(path, format="PNG")
    logger.debug(f"テスト画像を作成: {path}")
    return path


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture()
async def browser_context():
    """Playwrightブラウザコンテキストを作成し、終了後にクリーンアップ."""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        locale="ja-JP",
    )
    yield context
    await context.close()
    await browser.close()
    await pw.stop()


@pytest.fixture()
async def logged_in_page(browser_context: BrowserContext) -> Page:
    """ログイン済みページを返すフィクスチャ."""
    page = await browser_context.new_page()
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    await page.fill("input[name='email']", "e2e@test.com")
    await page.click("button[type='submit']")
    await page.wait_for_url(f"{BASE_URL}/home")
    logger.info("ログイン完了 (e2e@test.com)")
    return page


# ---------------------------------------------------------------------------
# テスト
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_home_shows_guest_when_not_logged_in(
    browser_context: BrowserContext,
):
    """未ログイン時にホーム画面で 'Guest' が表示されること."""
    page = await browser_context.new_page()
    await page.goto(f"{BASE_URL}/home", wait_until="networkidle")

    guest_label = page.locator("span.guest-label")
    assert await guest_label.count() > 0, "Guest ラベルが見つからない"
    assert await guest_label.text_content() == "Guest"
    logger.info("Guest ラベルを確認")


@pytest.mark.asyncio
async def test_login_via_email(browser_context: BrowserContext):
    """メールアドレスでログインし、ホーム画面にユーザー名が表示されること."""
    page = await browser_context.new_page()
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle")

    await page.fill("input[name='email']", "alice@example.com")
    await page.click("button[type='submit']")
    await page.wait_for_url(f"{BASE_URL}/home")

    user_name = page.locator("span.user-name")
    assert await user_name.count() > 0, "ユーザー名が表示されていない"
    assert await user_name.text_content() == "alice"
    logger.info("メールログイン成功: alice")


@pytest.mark.asyncio
async def test_login_via_google(browser_context: BrowserContext):
    """Googleログインリンクでログインできること."""
    page = await browser_context.new_page()
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle")

    await page.click("a:has-text('Continue with Google')")
    await page.wait_for_url(f"{BASE_URL}/home")

    user_name = page.locator("span.user-name")
    assert await user_name.count() > 0, "ユーザー名が表示されていない"
    assert await user_name.text_content() == "Google User"
    logger.info("Googleログイン成功")


@pytest.mark.asyncio
async def test_create_text_post(logged_in_page: Page):
    """テキスト投稿を作成し、タイムラインに表示されること."""
    page = logged_in_page
    post_text = "E2Eテスト投稿 テキストのみ"

    await page.fill("textarea[name='text']", post_text)
    await page.click("button[type='submit']:has-text('Post')")
    await page.wait_for_url(f"{BASE_URL}/home")
    await page.wait_for_load_state("networkidle")

    post_card = page.locator(".post-text", has_text=post_text)
    assert await post_card.count() > 0, "投稿がタイムラインに表示されていない"
    logger.info("テキスト投稿を確認")


@pytest.mark.asyncio
async def test_create_post_with_image(
    logged_in_page: Page,
    tmp_path: Path,
):
    """画像付き投稿を作成し、タイムラインに画像が表示されること."""
    page = logged_in_page
    image_path = _create_test_image(tmp_path, "post_image.png")
    post_text = "E2Eテスト 画像付き投稿"

    await page.fill("textarea[name='text']", post_text)
    file_input = page.locator("input[type='file'][name='images']")
    await file_input.set_input_files(str(image_path))
    await page.click("button[type='submit']:has-text('Post')")
    await page.wait_for_url(f"{BASE_URL}/home")
    await page.wait_for_load_state("networkidle")

    post_card = page.locator(".post-text", has_text=post_text)
    assert await post_card.count() > 0, "投稿がタイムラインに表示されていない"

    post_images = page.locator(".post-images img")
    assert await post_images.count() > 0, "投稿画像が表示されていない"
    logger.info("画像付き投稿を確認")


@pytest.mark.asyncio
async def test_create_story(
    logged_in_page: Page,
    tmp_path: Path,
):
    """ストーリーを作成できること."""
    page = logged_in_page
    image_path = _create_test_image(tmp_path, "story_image.png")

    # ストーリーモーダルを開く
    await page.click(".story-add-button")
    modal = page.locator("#story-modal")
    await modal.wait_for(state="visible")

    # 画像をアップロードしてテキストを入力
    file_input = modal.locator("input[type='file'][name='image']")
    await file_input.set_input_files(str(image_path))
    await modal.locator("input[name='text']").fill("E2Eストーリーテスト")

    await modal.locator("button[type='submit']:has-text('投稿')").click()
    await page.wait_for_url(f"{BASE_URL}/home")
    await page.wait_for_load_state("networkidle")

    story_items = page.locator("[data-testid='story']")
    assert await story_items.count() > 0, "ストーリーが表示されていない"
    logger.info("ストーリー作成を確認")


@pytest.mark.asyncio
async def test_api_posts_endpoint(
    logged_in_page: Page,
):
    """投稿後に /api/posts で投稿データが取得できること."""
    page = logged_in_page
    post_text = "APIエンドポイントテスト投稿"

    await page.fill("textarea[name='text']", post_text)
    await page.click("button[type='submit']:has-text('Post')")
    await page.wait_for_url(f"{BASE_URL}/home")
    await page.wait_for_load_state("networkidle")

    # API から投稿を取得
    api_response = await page.goto(f"{BASE_URL}/api/posts")
    assert api_response is not None
    assert api_response.status == 200

    data = await api_response.json()
    texts = [p["text"] for p in data["posts"]]
    assert post_text in texts, f"APIレスポンスに投稿が含まれていない: {texts}"
    logger.info("API /api/posts を確認")


@pytest.mark.asyncio
async def test_session_persistence(
    browser_context: BrowserContext,
    tmp_path: Path,
):
    """セッションを保存・復元してログイン状態が維持されること."""
    # ログイン
    page = await browser_context.new_page()
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    await page.fill("input[name='email']", "persist@test.com")
    await page.click("button[type='submit']")
    await page.wait_for_url(f"{BASE_URL}/home")

    user_name = page.locator("span.user-name")
    assert await user_name.text_content() == "persist"

    # ストレージステートを保存
    state_path = tmp_path / "state.json"
    state = await browser_context.storage_state()
    state_path.write_text(json.dumps(state), encoding="utf-8")
    await page.close()

    # 新しいコンテキストを保存したステートから作成
    pw = await async_playwright().start()
    browser2 = await pw.chromium.launch(headless=True)
    context2 = await browser2.new_context(
        storage_state=str(state_path),
        viewport={"width": 1280, "height": 800},
    )

    try:
        page2 = await context2.new_page()
        await page2.goto(f"{BASE_URL}/home", wait_until="networkidle")

        user_name2 = page2.locator("span.user-name")
        assert await user_name2.count() > 0, "復元後にユーザー名が表示されていない"
        assert await user_name2.text_content() == "persist"
        logger.info("セッション永続化を確認")
    finally:
        await context2.close()
        await browser2.close()
        await pw.stop()
