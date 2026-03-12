"""Manager E2E tests.

Verify that AuthManager, PostManager, and StoryManager
work correctly against the test server.
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
# Helpers
# ---------------------------------------------------------------------------


def _create_test_image(directory: Path, name: str = "test.png") -> Path:
    """Generate and return a 100x100 red test PNG image."""
    path = directory / name
    img = Image.new("RGB", (100, 100), color="red")
    img.save(path, format="PNG")
    logger.debug(f"Created test image: {path}")
    return path


def _make_settings() -> AppSettings:
    """Generate AppSettings for testing."""
    return AppSettings(
        test_mode=True,
        test_server_url=BASE_URL,
        browser={"headless": True, "slow_mo": 0},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def settings() -> AppSettings:
    """Settings for testing."""
    return _make_settings()


@pytest.fixture()
async def managed_context(settings: AppSettings):
    """Start a browser context via SessionManager and clean up after the test."""
    from src.browser.session import SessionManager

    sm = SessionManager(settings)
    # Clear any leftover session from previous tests
    sm.clear_session()
    context = await sm.start()
    yield context
    await sm.close()


async def _login_context(context: BrowserContext) -> None:
    """Helper to perform email login within a context."""
    page = await context.new_page()
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    await page.fill("input[name='email']", "manager_test@example.com")
    await page.click("button[type='submit']")
    await page.wait_for_url(f"{BASE_URL}/home")
    await page.close()
    logger.info("Helper login complete: manager_test@example.com")


# ---------------------------------------------------------------------------
# AuthManager Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_manager_detects_not_logged_in(
    settings: AppSettings,
    managed_context: BrowserContext,
):
    """Verify that AuthManager correctly detects not-logged-in state."""
    auth = AuthManager(settings)
    page = await managed_context.new_page()

    result = await auth.is_logged_in(page)
    assert result is False, "Expected False for not-logged-in state"
    logger.info("AuthManager: not-logged-in detection OK")
    await page.close()


@pytest.mark.asyncio
async def test_auth_manager_detects_logged_in(
    settings: AppSettings,
    managed_context: BrowserContext,
):
    """Verify that AuthManager correctly detects logged-in state."""
    await _login_context(managed_context)

    auth = AuthManager(settings)
    page = await managed_context.new_page()

    result = await auth.is_logged_in(page)
    assert result is True, "Expected True for logged-in state"
    logger.info("AuthManager: logged-in detection OK")
    await page.close()


# ---------------------------------------------------------------------------
# PostManager Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_manager_creates_text_post(
    settings: AppSettings,
    managed_context: BrowserContext,
):
    """Verify PostManager creates a text post and it appears via API."""
    await _login_context(managed_context)

    pm = PostManager(settings)
    post_text = "Manager test - text post"
    ok = await pm.create_post(managed_context, text=post_text)
    assert ok is True, "PostManager.create_post returned False"

    # Verify via API
    page = await managed_context.new_page()
    resp = await page.goto(f"{BASE_URL}/api/posts")
    assert resp is not None and resp.status == 200
    data = await resp.json()
    texts = [p["text"] for p in data["posts"]]
    assert post_text in texts, f"Post not found in API: {texts}"
    logger.info("PostManager: text post verified")
    await page.close()


@pytest.mark.asyncio
async def test_post_manager_creates_image_post(
    settings: AppSettings,
    managed_context: BrowserContext,
    tmp_path: Path,
):
    """Verify PostManager creates a post with images and image URLs are present in API."""
    await _login_context(managed_context)

    image_path = _create_test_image(tmp_path, "mgr_post_img.png")
    pm = PostManager(settings)
    post_text = "Manager test - image post"
    ok = await pm.create_post(
        managed_context,
        text=post_text,
        image_paths=[image_path],
    )
    assert ok is True, "PostManager.create_post (image) returned False"

    # Verify via API
    page = await managed_context.new_page()
    resp = await page.goto(f"{BASE_URL}/api/posts")
    assert resp is not None and resp.status == 200
    data = await resp.json()
    matched = [p for p in data["posts"] if p["text"] == post_text]
    assert len(matched) > 0, "Image post not found in API"
    assert len(matched[0]["images"]) > 0, "Image URLs are empty"
    logger.info("PostManager: image post verified")
    await page.close()


# ---------------------------------------------------------------------------
# StoryManager Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_story_manager_uploads_story(
    settings: AppSettings,
    managed_context: BrowserContext,
    tmp_path: Path,
):
    """Verify StoryManager uploads a story and it appears via API."""
    await _login_context(managed_context)

    image_path = _create_test_image(tmp_path, "mgr_story_img.png")
    sm = StoryManager(settings)
    ok = await sm.upload_story(
        managed_context,
        image_path=image_path,
        text="Manager story test",
    )
    assert ok is True, "StoryManager.upload_story returned False"

    # Verify via API
    page = await managed_context.new_page()
    resp = await page.goto(f"{BASE_URL}/api/stories")
    assert resp is not None and resp.status == 200
    data = await resp.json()
    assert len(data["stories"]) > 0, "Story not found in API"
    latest = data["stories"][-1]
    assert latest["image"] is not None, "Story image URL is None"
    logger.info("StoryManager: story upload verified")
    await page.close()
