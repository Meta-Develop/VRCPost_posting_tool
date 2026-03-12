"""E2E tests.

Full-flow E2E tests against the local test server using Playwright.
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
# Helpers
# ---------------------------------------------------------------------------


def _create_test_image(directory: Path, name: str = "test.png") -> Path:
    """Generate and return a 100x100 red test PNG image."""
    path = directory / name
    img = Image.new("RGB", (100, 100), color="red")
    img.save(path, format="PNG")
    logger.debug(f"Created test image: {path}")
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def browser_context():
    """Create a Playwright browser context and clean up after the test."""
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
    """Return a fixture providing a logged-in page."""
    page = await browser_context.new_page()
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    await page.fill("input[name='email']", "e2e@test.com")
    await page.click("button[type='submit']")
    await page.wait_for_url(f"{BASE_URL}/home")
    logger.info("Login complete (e2e@test.com)")
    return page


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_home_shows_guest_when_not_logged_in(
    browser_context: BrowserContext,
):
    """Verify that 'Guest' is displayed on the home page when not logged in."""
    page = await browser_context.new_page()
    await page.goto(f"{BASE_URL}/home", wait_until="networkidle")

    guest_label = page.locator("span.guest-label")
    assert await guest_label.count() > 0, "Guest label not found"
    assert await guest_label.text_content() == "Guest"
    logger.info("Guest label verified")


@pytest.mark.asyncio
async def test_login_via_email(browser_context: BrowserContext):
    """Verify login by email and that the username appears on the home page."""
    page = await browser_context.new_page()
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle")

    await page.fill("input[name='email']", "alice@example.com")
    await page.click("button[type='submit']")
    await page.wait_for_url(f"{BASE_URL}/home")

    user_name = page.locator("span.user-name")
    assert await user_name.count() > 0, "Username not displayed"
    assert await user_name.text_content() == "alice"
    logger.info("Email login successful: alice")


@pytest.mark.asyncio
async def test_login_via_google(browser_context: BrowserContext):
    """Verify login via Google link."""
    page = await browser_context.new_page()
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle")

    await page.click("a:has-text('Continue with Google')")
    await page.wait_for_url(f"{BASE_URL}/home")

    user_name = page.locator("span.user-name")
    assert await user_name.count() > 0, "Username not displayed"
    assert await user_name.text_content() == "Google User"
    logger.info("Google login successful")


@pytest.mark.asyncio
async def test_create_text_post(logged_in_page: Page):
    """Verify that a text-only post can be created and appears on the timeline."""
    page = logged_in_page
    post_text = "E2E test post - text only"

    await page.fill("textarea[name='text']", post_text)
    await page.click("button[type='submit']:has-text('Post')")
    await page.wait_for_url(f"{BASE_URL}/home")
    await page.wait_for_load_state("networkidle")

    post_card = page.locator(".post-text", has_text=post_text)
    assert await post_card.count() > 0, "Post not found on timeline"
    logger.info("Text post verified")


@pytest.mark.asyncio
async def test_create_post_with_image(
    logged_in_page: Page,
    tmp_path: Path,
):
    """Verify that a post with an image can be created and the image is displayed."""
    page = logged_in_page
    image_path = _create_test_image(tmp_path, "post_image.png")
    post_text = "E2E test - post with image"

    await page.fill("textarea[name='text']", post_text)
    file_input = page.locator("input[type='file'][name='images']")
    await file_input.set_input_files(str(image_path))
    await page.click("button[type='submit']:has-text('Post')")
    await page.wait_for_url(f"{BASE_URL}/home")
    await page.wait_for_load_state("networkidle")

    post_card = page.locator(".post-text", has_text=post_text)
    assert await post_card.count() > 0, "Post not found on timeline"

    post_images = page.locator(".post-images img")
    assert await post_images.count() > 0, "Post images not displayed"
    logger.info("Image post verified")


@pytest.mark.asyncio
async def test_create_story(
    logged_in_page: Page,
    tmp_path: Path,
):
    """Verify that a story can be created."""
    page = logged_in_page
    image_path = _create_test_image(tmp_path, "story_image.png")

    # Open story modal
    await page.click(".story-add-button")
    modal = page.locator("#story-modal")
    await modal.wait_for(state="visible")

    # Upload image and enter text
    file_input = modal.locator("input[type='file'][name='image']")
    await file_input.set_input_files(str(image_path))
    await modal.locator("input[name='text']").fill("E2E story test")

    await modal.locator("button[type='submit']:has-text('Post')").click()
    await page.wait_for_url(f"{BASE_URL}/home")
    await page.wait_for_load_state("networkidle")

    story_items = page.locator("[data-testid='story']")
    assert await story_items.count() > 0, "Story not displayed"
    logger.info("Story creation verified")


@pytest.mark.asyncio
async def test_api_posts_endpoint(
    logged_in_page: Page,
):
    """Verify that post data can be retrieved via /api/posts after posting."""
    page = logged_in_page
    post_text = "API endpoint test post"

    await page.fill("textarea[name='text']", post_text)
    await page.click("button[type='submit']:has-text('Post')")
    await page.wait_for_url(f"{BASE_URL}/home")
    await page.wait_for_load_state("networkidle")

    # Fetch posts via API
    api_response = await page.goto(f"{BASE_URL}/api/posts")
    assert api_response is not None
    assert api_response.status == 200

    data = await api_response.json()
    texts = [p["text"] for p in data["posts"]]
    assert post_text in texts, f"Post not found in API response: {texts}"
    logger.info("API /api/posts verified")


@pytest.mark.asyncio
async def test_session_persistence(
    browser_context: BrowserContext,
    tmp_path: Path,
):
    """Verify that login state persists after saving and restoring the session."""
    # Login
    page = await browser_context.new_page()
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    await page.fill("input[name='email']", "persist@test.com")
    await page.click("button[type='submit']")
    await page.wait_for_url(f"{BASE_URL}/home")

    user_name = page.locator("span.user-name")
    assert await user_name.text_content() == "persist"

    # Save storage state
    state_path = tmp_path / "state.json"
    state = await browser_context.storage_state()
    state_path.write_text(json.dumps(state), encoding="utf-8")
    await page.close()

    # Create new context from saved state
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
        assert await user_name2.count() > 0, "Username not displayed after restore"
        assert await user_name2.text_content() == "persist"
        logger.info("Session persistence verified")
    finally:
        await context2.close()
        await browser2.close()
        await pw.stop()
