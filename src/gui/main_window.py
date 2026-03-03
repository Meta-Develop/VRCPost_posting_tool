"""メインウィンドウ (CustomTkinter).

サイドバーナビゲーション + コンテンツ切替の
モダンなシングルウィンドウ UI。
"""

from __future__ import annotations

import customtkinter as ctk
from loguru import logger

from src.config.settings import AppSettings
from src.gui.events import EventEmitter
from src.utils.logger import setup_logger

# ── 外観 ──
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

SIDEBAR_W = 200
ACCENT = "#6366f1"
ACCENT_HOVER = "#818cf8"


class App(ctk.CTk):
    """アプリケーションメインウィンドウ."""

    def __init__(self) -> None:
        super().__init__()
        self.title("VRCPost Posting Tool")
        self.geometry("1120x720")
        self.minsize(900, 560)

        # ── 共有オブジェクト ──
        self.settings = AppSettings.load()
        self.emitter = EventEmitter()

        # ブラウザブリッジ (遅延起動)
        from src.browser.bridge import BrowserBridge

        self.bridge = BrowserBridge(self.settings, self.emitter)

        # スケジューラー
        from src.scheduler.connector import SchedulerConnector
        from src.scheduler.engine import SchedulerEngine

        self._engine = SchedulerEngine(self.settings)
        self.connector = SchedulerConnector(self._engine, self.bridge, self.emitter)

        # 通知
        from src.utils.notifier import NotificationManager

        self.notifier = NotificationManager(self.emitter)

        # ── UI 構築 ──
        self._build_sidebar()
        self._build_content()
        self._build_statusbar()

        # ── タブ生成 ──
        self._tabs: dict[str, ctk.CTkFrame] = {}
        self._create_tabs()
        self._show_tab("post")

        # ── イベント接続 ──
        self._connect_events()

        # ── 起動 ──
        self.bridge.start()
        self.connector.start()
        self._poll_events()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── サイドバー ────────────────────────────────────

    def _build_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(self, width=SIDEBAR_W, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # タイトル
        ctk.CTkLabel(
            self.sidebar,
            text="VRCPost",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(24, 2))
        ctk.CTkLabel(
            self.sidebar,
            text="Posting Tool",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).pack(pady=(0, 20))

        # ナビボタン
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        nav_items = [
            ("post", "投稿"),
            ("story", "ストーリー"),
            ("random", "ランダム投稿"),
            ("calendar", "カレンダー"),
            ("schedule", "スケジュール"),
            ("settings", "設定"),
            ("log", "ログ"),
        ]
        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                fg_color="transparent",
                text_color="gray90",
                hover_color=("gray75", "gray30"),
                anchor="w",
                height=36,
                corner_radius=8,
                command=lambda k=key: self._show_tab(k),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self._nav_buttons[key] = btn

        # スペーサー
        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(expand=True)

        # ログインボタン
        self._login_btn = ctk.CTkButton(
            self.sidebar,
            text="ログイン",
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            height=36,
            corner_radius=8,
            command=self._on_login,
        )
        self._login_btn.pack(fill="x", padx=12, pady=(4, 4))

        # モード表示
        mode_text = "テストモード" if self.settings.test_mode else "本番モード"
        self._mode_label = ctk.CTkLabel(
            self.sidebar,
            text=mode_text,
            font=ctk.CTkFont(size=11),
            text_color="orange" if self.settings.test_mode else "green",
        )
        self._mode_label.pack(pady=(0, 16))

    # ── コンテンツエリア ──────────────────────────────

    def _build_content(self) -> None:
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True)

    # ── ステータスバー ────────────────────────────────

    def _build_statusbar(self) -> None:
        self._statusbar = ctk.CTkLabel(
            self,
            text="起動中...",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
            height=24,
        )
        self._statusbar.pack(side="bottom", fill="x", padx=8)

    # ── タブ管理 ──────────────────────────────────────

    def _create_tabs(self) -> None:
        from src.gui.calendar_tab import CalendarTab
        from src.gui.log_tab import LogTab
        from src.gui.post_tab import PostTab
        from src.gui.random_post_tab import RandomPostTab
        from src.gui.schedule_tab import ScheduleTab
        from src.gui.settings_tab import SettingsTab
        from src.gui.story_tab import StoryTab

        self._tabs["post"] = PostTab(self.content, self)
        self._tabs["story"] = StoryTab(self.content, self)
        self._tabs["random"] = RandomPostTab(self.content, self)
        self._tabs["calendar"] = CalendarTab(self.content, self)
        self._tabs["schedule"] = ScheduleTab(self.content, self)
        self._tabs["settings"] = SettingsTab(self.content, self)
        self._tabs["log"] = LogTab(self.content, self)

    def _show_tab(self, name: str) -> None:
        for tab in self._tabs.values():
            tab.pack_forget()
        self._tabs[name].pack(fill="both", expand=True, padx=16, pady=16)

        # ナビハイライト
        for key, btn in self._nav_buttons.items():
            if key == name:
                btn.configure(fg_color=ACCENT, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color="gray90")

        # タブ固有のリフレッシュ
        tab = self._tabs[name]
        if hasattr(tab, "on_show"):
            tab.on_show()

    # ── イベント ──────────────────────────────────────

    def _connect_events(self) -> None:
        self.emitter.on("status_changed", self._set_status)
        self.emitter.on("login_success", lambda: self._set_login_state(True))
        self.emitter.on("login_failed", lambda: self._set_login_state(False))
        self.emitter.on("notification", self._show_toast)

    def _poll_events(self) -> None:
        self.emitter.process_pending()
        self.after(100, self._poll_events)

    def _set_status(self, text: str) -> None:
        self._statusbar.configure(text=text)

    def _set_login_state(self, ok: bool) -> None:
        if ok:
            self._login_btn.configure(text="ログイン済み", fg_color="green")
        else:
            self._login_btn.configure(text="ログイン", fg_color=ACCENT)

    def _on_login(self) -> None:
        self.bridge.login()

    # ── トースト通知 ──────────────────────────────────

    def _show_toast(self, title: str, message: str, level: str = "info") -> None:
        colors = {"info": "#3b82f6", "warning": "#f59e0b", "error": "#ef4444"}
        bg = colors.get(level, "#3b82f6")

        toast = ctk.CTkFrame(self, fg_color=bg, corner_radius=10)
        toast.place(relx=1.0, rely=0.0, anchor="ne", x=-20, y=20)

        ctk.CTkLabel(
            toast,
            text=f"{title}\n{message}",
            font=ctk.CTkFont(size=12),
            text_color="white",
            wraplength=280,
            justify="left",
        ).pack(padx=16, pady=10)

        # 4秒後にフェードアウト
        self.after(4000, toast.destroy)

    # ── 終了処理 ──────────────────────────────────────

    def _on_close(self) -> None:
        logger.info("アプリケーション終了")
        self.settings.save()
        self.connector.stop()
        self.bridge.shutdown()
        self.destroy()


def main() -> None:
    """アプリケーションエントリーポイント."""
    setup_logger()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
