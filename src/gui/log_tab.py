"""Log tab (CustomTkinter).

Display loguru logs in real time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk
from loguru import logger

if TYPE_CHECKING:
    from src.gui.main_window import App

# Log level -> color
LEVEL_COLORS = {
    "DEBUG": "#6b7280",
    "INFO": "#3b82f6",
    "WARNING": "#f59e0b",
    "ERROR": "#ef4444",
    "CRITICAL": "#dc2626",
}


class LogTab(ctk.CTkFrame):
    """Log tab."""

    def __init__(self, parent: ctk.CTkFrame, app: App) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._all_logs: list[tuple[str, str]] = []  # (level, formatted)
        self._current_filter = "ALL"
        self._build_ui()
        self._install_sink()

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            header, text="Logs", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            header, text="Clear", width=60, height=28, corner_radius=6,
            fg_color="gray40", command=self._clear,
        ).pack(side="right")

        # Filter
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

        # Log display area
        self._textbox = ctk.CTkTextbox(
            self,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled",
            wrap="word",
        )
        self._textbox.pack(fill="both", expand=True)

    # ── loguru sink ──

    def _install_sink(self) -> None:
        logger.add(self._log_sink, format="{time:HH:mm:ss} | {level: <8} | {message}")

    def _log_sink(self, message: str) -> None:
        record = message.record
        level = record["level"].name
        formatted = str(message).rstrip("\n")
        self._all_logs.append((level, formatted))

        # Max retained lines
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
            pass  # Prevent writes after widget destruction

    # ── Filter ──

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

    # ── Clear ──

    def _clear(self) -> None:
        self._all_logs.clear()
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")
