"""アプリケーション設定管理.

Pydantic Settingsを使って型安全に設定を管理する。
設定はJSON形式で永続化される。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# デフォルトの設定ディレクトリ
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


class BrowserSettings(BaseModel):
    """ブラウザ関連の設定."""

    headless: bool = Field(default=False, description="ヘッドレスモードで実行するか")
    timeout_ms: int = Field(default=30000, description="ページ読み込みタイムアウト(ms)")
    user_data_dir: str = Field(
        default="config/browser_data", description="ブラウザのユーザーデータ保存先"
    )
    slow_mo: int = Field(default=100, description="操作間のスローモーション(ms)")


class SchedulerSettings(BaseModel):
    """スケジューラー関連の設定."""

    timezone: str = Field(default="Asia/Tokyo", description="タイムゾーン")
    max_retries: int = Field(default=3, description="失敗時の最大リトライ回数")
    retry_interval_sec: int = Field(default=60, description="リトライ間隔(秒)")
    jobs_file: str = Field(
        default="config/scheduled_jobs.json", description="スケジュールジョブの保存先"
    )


class PostSettings(BaseModel):
    """投稿関連の設定."""

    default_hashtags: list[str] = Field(
        default_factory=list, description="デフォルトのハッシュタグ"
    )
    max_images: int = Field(default=4, description="一投稿あたりの最大画像数")
    image_max_size_kb: int = Field(default=5120, description="画像の最大サイズ(KB)")
    image_max_width: int = Field(default=1920, description="画像の最大幅(px)")
    image_max_height: int = Field(default=1920, description="画像の最大高さ(px)")


class AppSettings(BaseSettings):
    """アプリケーション全体の設定."""

    base_url: str = Field(default="https://vrcpost.com", description="VRCPostのベースURL")
    test_mode: bool = Field(default=True, description="テストモード（テストサーバー使用）")
    test_server_url: str = Field(
        default="http://localhost:5000", description="テストサーバーのURL"
    )
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    post: PostSettings = Field(default_factory=PostSettings)

    @property
    def active_url(self) -> str:
        """現在アクティブなURL（テストモードならテストサーバー）."""
        return self.test_server_url if self.test_mode else self.base_url

    def save(self, path: Optional[Path] = None) -> None:
        """設定をJSONファイルに保存."""
        save_path = path or SETTINGS_FILE
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppSettings":
        """JSONファイルから設定を読み込み."""
        load_path = path or SETTINGS_FILE
        if load_path.exists():
            with open(load_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        return cls()
