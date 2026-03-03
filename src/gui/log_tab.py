"""ログタブ (CustomTkinter).

loguru のログをリアルタイムで表示する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk
from loguru import logger

if TYPE_CHECKING:
    from src.gui.main_window import App

# ログレベル → 色
LEVEL_COLORS = {
    "DEBUG": "#6b7280",
    "INFO": "#3b82f6",
    "WARNING": "#f59e0b",
    "ERROR": "#ef4444",
    "CRITICAL": "#dc2626",
}


class LogTab(ctk.CTkFrame):
    """ログタブ."""

    def __init__(self, parent: ctk.CTkFrame, app: App) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._all_logs: list[tuple[str, str]] = []  # (level, formatted)
        self._current_filter = "ALL"
        self._build_ui()
        self._install_sink()

    def _build_ui(self) -> None:
        # ヘッダー
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            header, text="ログ", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            header, text="クリア", width=60, height=28, corner_radius=6,
            fg_color="gray40", command=self._clear,
        ).pack(side="right")

        # フィルター
        self._filter_var = ctk.StringVar(value="ALL")
        filter_frame = ctk.CTkFrame(header, fg_color="transparent")
        filter_frame.pack(side="right", padx=12)
        for level in ["ALL", "DEBUG", "INFO", "WARNING", "ERROR"]:
            ctk.CTkRadioButton(
                filter_frame,
                text=level,
                variable=self._filter_var,
                value=level,
                radiobutton_width=14,
                radiobutton_height=14,
                command=self._apply_filter,
            ).pack(side="left", padx=4)

        # ログ表示エリア
        self._textbox = ctk.CTkTextbox(
            self,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled",
            wrap="word",
        )
        self._textbox.pack(fill="both", expand=True)

    # ── loguru シンク ──

    def _install_sink(self) -> None:
        logger.add(self._log_sink, format="{time:HH:mm:ss} | {level: <8} | {message}")

    def _log_sink(self, message: str) -> None:
        record = message.record
        level = record["level"].name
        formatted = str(message).rstrip("\n")
        self._all_logs.append((level, formatted))

        # 最大保持行数
        if len(self._all_logs) > 5000:
            self._all_logs = self._all_logs[-3000:]

        if self._current_filter == "ALL" or level == self._current_filter:
            self._append_line(formatted)

    def _append_line(self, text: str) -> None:
        try:
            self._textbox.configure(state="normal")
            self._textbox.insert("end", text + "\n")
            self._textbox.see("end")
            self._textbox.configure(state="disabled")
        except Exception:
            pass  # ウィジェット破棄後の書き込み防止

    # ── フィルター ──

    def _apply_filter(self) -> None:
        self._current_filter = self._filter_var.get()
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")

        levels_order = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        min_idx = 0
        if self._current_filter != "ALL":
            min_idx = levels_order.index(self._current_filter)

        for level, line in self._all_logs:
            try:
                if levels_order.index(level) >= min_idx:
                    self._append_line(line)
            except ValueError:
                self._append_line(line)

    # ── クリア ──

    def _clear(self) -> None:
        self._all_logs.clear()
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")
