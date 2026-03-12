"""Application settings management.

Uses Pydantic Settings for type-safe configuration.
Settings are persisted in JSON format.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# Default config directory
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


class BrowserSettings(BaseModel):
    """Browser-related settings."""

    headless: bool = Field(default=False, description="Run in headless mode")
    timeout_ms: int = Field(default=30000, description="Page load timeout (ms)")
    user_data_dir: str = Field(
        default="config/browser_data", description="Browser user data directory"
    )
    slow_mo: int = Field(default=100, description="Slow motion between operations (ms)")


class SchedulerSettings(BaseModel):
    """Scheduler-related settings."""

    timezone: str = Field(default="Asia/Tokyo", description="Timezone")
    max_retries: int = Field(default=3, description="Max retries on failure")
    retry_interval_sec: int = Field(default=60, description="Retry interval (seconds)")
    jobs_file: str = Field(
        default="config/scheduled_jobs.json", description="Scheduled jobs file path"
    )


class PostSettings(BaseModel):
    """Post-related settings."""

    default_hashtags: list[str] = Field(
        default_factory=list, description="Default hashtags"
    )
    max_images: int = Field(default=4, description="Max images per post")
    image_max_size_kb: int = Field(default=5120, description="Max image size (KB)")
    image_max_width: int = Field(default=1920, description="Max image width (px)")
    image_max_height: int = Field(default=1920, description="Max image height (px)")


class AppSettings(BaseSettings):
    """Application-wide settings."""

    base_url: str = Field(default="https://vrcpost.com", description="VRCPost base URL")
    test_mode: bool = Field(default=True, description="Test mode (use test server)")
    test_server_url: str = Field(
        default="http://localhost:5000", description="Test server URL"
    )
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    post: PostSettings = Field(default_factory=PostSettings)

    @property
    def active_url(self) -> str:
        """Active URL (test server in test mode)."""
        return self.test_server_url if self.test_mode else self.base_url

    def save(self, path: Optional[Path] = None) -> None:
        """Save settings to a JSON file."""
        save_path = path or SETTINGS_FILE
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppSettings":
        """Load settings from a JSON file."""
        load_path = path or SETTINGS_FILE
        if load_path.exists():
            with open(load_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        return cls()
