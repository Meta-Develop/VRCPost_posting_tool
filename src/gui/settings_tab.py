"""設定タブ (CustomTkinter).

アプリケーション設定の表示・編集を提供する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from src.gui.main_window import App


class SettingsTab(ctk.CTkFrame):
    """設定タブ."""

    def __init__(self, parent: ctk.CTkFrame, app: App) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._entries: dict[str, ctk.CTkEntry | ctk.CTkSwitch] = {}
        self._vars: dict[str, ctk.BooleanVar] = {}
        self._build_ui()
        self._load_values()

    # ── UI 構築 ──

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self, text="設定", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", pady=(0, 12))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # ── 接続 ──
        self._section(scroll, "接続設定")
        self._add_entry(scroll, "base_url", "本番 URL")
        self._add_entry(scroll, "test_server_url", "テストサーバー URL")
        self._add_switch(scroll, "test_mode", "テストモード")

        # ── ブラウザ ──
        self._section(scroll, "ブラウザ設定")
        self._add_switch(scroll, "headless", "ヘッドレスモード")
        self._add_entry(scroll, "timeout_ms", "タイムアウト (ms)")
        self._add_entry(scroll, "slow_mo", "スローモーション (ms)")

        # ── 投稿 ──
        self._section(scroll, "投稿設定")
        self._add_entry(scroll, "max_images", "最大画像数")
        self._add_entry(scroll, "image_max_size_kb", "画像最大サイズ (KB)")
        self._add_entry(scroll, "image_max_width", "画像最大幅 (px)")
        self._add_entry(scroll, "image_max_height", "画像最大高さ (px)")
        self._add_entry(scroll, "default_hashtags", "デフォルトハッシュタグ")

        # ── スケジューラー ──
        self._section(scroll, "スケジューラー設定")
        self._add_entry(scroll, "timezone", "タイムゾーン")
        self._add_entry(scroll, "max_retries", "最大リトライ")
        self._add_entry(scroll, "retry_interval_sec", "リトライ間隔 (秒)")

        # ボタン
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(12, 0))
        ctk.CTkButton(
            btn_frame,
            text="保存",
            height=36,
            corner_radius=8,
            fg_color="#6366f1",
            hover_color="#818cf8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._save,
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(
            btn_frame,
            text="リセット",
            height=36,
            corner_radius=8,
            fg_color="gray40",
            command=self._reset,
        ).pack(side="left", width=100)

    # ── ヘルパー ──

    def _section(self, parent: ctk.CTkFrame, title: str) -> None:
        ctk.CTkLabel(
            parent,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#6366f1",
        ).pack(anchor="w", pady=(16, 4))

    def _add_entry(self, parent: ctk.CTkFrame, key: str, label: str) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, width=180, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(row, corner_radius=6)
        entry.pack(side="left", expand=True, fill="x")
        self._entries[key] = entry

    def _add_switch(self, parent: ctk.CTkFrame, key: str, label: str) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, width=180, anchor="w").pack(side="left")
        var = ctk.BooleanVar()
        sw = ctk.CTkSwitch(row, text="", variable=var)
        sw.pack(side="left")
        self._vars[key] = var
        self._entries[key] = sw

    # ── 値の読み書き ──

    def _load_values(self) -> None:
        s = self.app.settings
        mapping: dict[str, str] = {
            "base_url": s.base_url,
            "test_server_url": s.test_server_url,
            "timeout_ms": str(s.browser.timeout_ms),
            "slow_mo": str(s.browser.slow_mo),
            "max_images": str(s.post.max_images),
            "image_max_size_kb": str(s.post.image_max_size_kb),
            "image_max_width": str(s.post.image_max_width),
            "image_max_height": str(s.post.image_max_height),
            "default_hashtags": ", ".join(s.post.default_hashtags),
            "timezone": s.scheduler.timezone,
            "max_retries": str(s.scheduler.max_retries),
            "retry_interval_sec": str(s.scheduler.retry_interval_sec),
        }
        for key, val in mapping.items():
            widget = self._entries.get(key)
            if isinstance(widget, ctk.CTkEntry):
                widget.delete(0, "end")
                widget.insert(0, val)

        self._vars.get("test_mode", ctk.BooleanVar()).set(s.test_mode)
        self._vars.get("headless", ctk.BooleanVar()).set(s.browser.headless)

    def _save(self) -> None:
        s = self.app.settings

        def _get(key: str) -> str:
            w = self._entries.get(key)
            if isinstance(w, ctk.CTkEntry):
                return w.get().strip()
            return ""

        s.base_url = _get("base_url") or s.base_url
        s.test_server_url = _get("test_server_url") or s.test_server_url
        s.test_mode = self._vars.get("test_mode", ctk.BooleanVar()).get()
        s.browser.headless = self._vars.get("headless", ctk.BooleanVar()).get()

        try:
            s.browser.timeout_ms = int(_get("timeout_ms"))
        except ValueError:
            pass
        try:
            s.browser.slow_mo = int(_get("slow_mo"))
        except ValueError:
            pass
        try:
            s.post.max_images = int(_get("max_images"))
        except ValueError:
            pass
        try:
            s.post.image_max_size_kb = int(_get("image_max_size_kb"))
        except ValueError:
            pass
        try:
            s.post.image_max_width = int(_get("image_max_width"))
        except ValueError:
            pass
        try:
            s.post.image_max_height = int(_get("image_max_height"))
        except ValueError:
            pass

        tags = _get("default_hashtags")
        s.post.default_hashtags = [t.strip() for t in tags.split(",") if t.strip()]

        s.scheduler.timezone = _get("timezone") or s.scheduler.timezone
        try:
            s.scheduler.max_retries = int(_get("max_retries"))
        except ValueError:
            pass
        try:
            s.scheduler.retry_interval_sec = int(_get("retry_interval_sec"))
        except ValueError:
            pass

        s.save()
        self.app.notifier.info("設定", "設定を保存しました")

        # モードラベル更新
        mode_text = "テストモード" if s.test_mode else "本番モード"
        color = "orange" if s.test_mode else "green"
        self.app._mode_label.configure(text=mode_text, text_color=color)

    def _reset(self) -> None:
        self._load_values()
        self.app.notifier.info("設定", "変更を元に戻しました")
