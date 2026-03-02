"""マネージャーE2Eテスト.

AuthManager, PostManager, StoryManager が
テストサーバーに対して正しく動作するか検証する。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from loguru import logger
from PIL import Image
from playwright.async_api import BrowserContext

from src.browser.auth import AuthManager
from src.browser.post import PostManager
from src.browser.story import StoryManager
from src.config.settings import AppSettings

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


def _make_settings() -> AppSettings:
    """テスト用の AppSettings を生成."""
    return AppSettings(
        test_mode=True,
        test_server_url=BASE_URL,
        browser={"headless": True, "slow_mo": 0},
    )


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture()
async def settings() -> AppSettings:
    """テスト用設定."""
    return _make_settings()


@pytest.fixture()
async def managed_context(settings: AppSettings):
    """SessionManager でブラウザコンテキストを起動し、終了後にクリーンアップ."""
    from src.browser.session import SessionManager

    sm = SessionManager(settings)
    # 前回テストのセッションが残っている場合はクリア
    sm.clear_session()
    context = await sm.start()
    yield context
    await sm.close()


async def _login_context(context: BrowserContext) -> None:
    """コンテキスト内でメールログインを実行するヘルパー."""
    page = await context.new_page()
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    await page.fill("input[name='email']", "manager_test@example.com")
    await page.click("button[type='submit']")
    await page.wait_for_url(f"{BASE_URL}/home")
    await page.close()
    logger.info("ヘルパーログイン完了: manager_test@example.com")


# ---------------------------------------------------------------------------
# AuthManager テスト
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_manager_detects_not_logged_in(
    settings: AppSettings,
    managed_context: BrowserContext,
):
    """未ログイン状態を AuthManager が正しく検出すること."""
    auth = AuthManager(settings)
    page = await managed_context.new_page()

    result = await auth.is_logged_in(page)
    assert result is False, "未ログインなのに True が返された"
    logger.info("AuthManager: 未ログイン検出OK")
    await page.close()


@pytest.mark.asyncio
async def test_auth_manager_detects_logged_in(
    settings: AppSettings,
    managed_context: BrowserContext,
):
    """ログイン済み状態を AuthManager が正しく検出すること."""
    await _login_context(managed_context)

    auth = AuthManager(settings)
    page = await managed_context.new_page()

    result = await auth.is_logged_in(page)
    assert result is True, "ログイン済みなのに False が返された"
    logger.info("AuthManager: ログイン済み検出OK")
    await page.close()


# ---------------------------------------------------------------------------
# PostManager テスト
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_manager_creates_text_post(
    settings: AppSettings,
    managed_context: BrowserContext,
):
    """PostManager でテキスト投稿を作成し、APIで確認できること."""
    await _login_context(managed_context)

    pm = PostManager(settings)
    post_text = "マネージャーテスト テキスト投稿"
    ok = await pm.create_post(managed_context, text=post_text)
    assert ok is True, "PostManager.create_post が False を返した"

    # API で確認
    page = await managed_context.new_page()
    resp = await page.goto(f"{BASE_URL}/api/posts")
    assert resp is not None and resp.status == 200
    data = await resp.json()
    texts = [p["text"] for p in data["posts"]]
    assert post_text in texts, f"投稿がAPIに存在しない: {texts}"
    logger.info("PostManager: テキスト投稿を確認")
    await page.close()


@pytest.mark.asyncio
async def test_post_manager_creates_image_post(
    settings: AppSettings,
    managed_context: BrowserContext,
    tmp_path: Path,
):
    """PostManager で画像付き投稿を作成し、APIで画像URLを確認できること."""
    await _login_context(managed_context)

    image_path = _create_test_image(tmp_path, "mgr_post_img.png")
    pm = PostManager(settings)
    post_text = "マネージャーテスト 画像投稿"
    ok = await pm.create_post(
        managed_context,
        text=post_text,
        image_paths=[image_path],
    )
    assert ok is True, "PostManager.create_post (画像) が False を返した"

    # API で確認
    page = await managed_context.new_page()
    resp = await page.goto(f"{BASE_URL}/api/posts")
    assert resp is not None and resp.status == 200
    data = await resp.json()
    matched = [p for p in data["posts"] if p["text"] == post_text]
    assert len(matched) > 0, "画像投稿がAPIに存在しない"
    assert len(matched[0]["images"]) > 0, "画像URLが空"
    logger.info("PostManager: 画像投稿を確認")
    await page.close()


# ---------------------------------------------------------------------------
# StoryManager テスト
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_story_manager_uploads_story(
    settings: AppSettings,
    managed_context: BrowserContext,
    tmp_path: Path,
):
    """StoryManager でストーリーをアップロードし、APIで確認できること."""
    await _login_context(managed_context)

    image_path = _create_test_image(tmp_path, "mgr_story_img.png")
    sm = StoryManager(settings)
    ok = await sm.upload_story(
        managed_context,
        image_path=image_path,
        text="マネージャーストーリーテスト",
    )
    assert ok is True, "StoryManager.upload_story が False を返した"

    # API で確認
    page = await managed_context.new_page()
    resp = await page.goto(f"{BASE_URL}/api/stories")
    assert resp is not None and resp.status == 200
    data = await resp.json()
    assert len(data["stories"]) > 0, "ストーリーがAPIに存在しない"
    latest = data["stories"][-1]
    assert latest["image"] is not None, "ストーリー画像URLがない"
    logger.info("StoryManager: ストーリーアップロードを確認")
    await page.close()
