"""Post tab (CustomTkinter).

Provides a UI for text input, image selection, and scheduled posting.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk
from loguru import logger
from PIL import Image

if TYPE_CHECKING:
    from src.gui.main_window import App

MAX_PREVIEW = 4
PREVIEW_SIZE = (120, 120)


class PostTab(ctk.CTkFrame):
    """Post tab."""

    def __init__(self, parent: ctk.CTkFrame, app: App) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._image_paths: list[Path] = []
        self._build_ui()

    # ── Build UI ──

    def _build_ui(self) -> None:
        # Header
        ctk.CTkLabel(
            self, text="Create Post", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", pady=(0, 12))

        # Text input
        ctk.CTkLabel(self, text="Text", font=ctk.CTkFont(size=13)).pack(anchor="w")
        self._text = ctk.CTkTextbox(self, height=120, corner_radius=8)
        self._text.pack(fill="x", pady=(4, 12))

        # Image section
        img_header = ctk.CTkFrame(self, fg_color="transparent")
        img_header.pack(fill="x")
        ctk.CTkLabel(
            img_header, text="Images (max 4)", font=ctk.CTkFont(size=13)
        ).pack(side="left")
        ctk.CTkButton(
            img_header,
            text="Add Images",
            width=100,
            height=28,
            corner_radius=6,
            command=self._add_images,
        ).pack(side="right")
        ctk.CTkButton(
            img_header,
            text="Clear",
            width=60,
            height=28,
            corner_radius=6,
            fg_color="gray40",
            command=self._clear_images,
        ).pack(side="right", padx=(0, 6))

        # Image preview
        self._preview_frame = ctk.CTkFrame(self, height=140, corner_radius=8)
        self._preview_frame.pack(fill="x", pady=(4, 12))
        self._preview_label = ctk.CTkLabel(
            self._preview_frame, text="No images", text_color="gray"
        )
        self._preview_label.pack(expand=True)

        # Scheduled post
        sched_frame = ctk.CTkFrame(self, fg_color="transparent")
        sched_frame.pack(fill="x", pady=(0, 12))
        self._schedule_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            sched_frame,
            text="Schedule Post",
            variable=self._schedule_var,
            command=self._toggle_schedule,
        ).pack(side="left")

        self._datetime_entry = ctk.CTkEntry(
            sched_frame,
            placeholder_text="2024/01/01 12:00",
            width=180,
            state="disabled",
        )
        self._datetime_entry.pack(side="left", padx=(16, 0))

        # Post button
        ctk.CTkButton(
            self,
            text="Post",
            height=40,
            corner_radius=8,
            fg_color="#6366f1",
            hover_color="#818cf8",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._do_post,
        ).pack(fill="x", pady=(8, 0))

    # ── Image operations ──

    def _add_images(self) -> None:
        files = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.gif *.webp *.bmp")],
        )
        if not files:
            return
        for f in files:
            if len(self._image_paths) >= MAX_PREVIEW:
                break
            self._image_paths.append(Path(f))
        self._refresh_previews()

    def _clear_images(self) -> None:
        self._image_paths.clear()
        self._refresh_previews()

    def _refresh_previews(self) -> None:
        for w in self._preview_frame.winfo_children():
            w.destroy()

        if not self._image_paths:
            self._preview_label = ctk.CTkLabel(
                self._preview_frame, text="No images", text_color="gray"
            )
            self._preview_label.pack(expand=True)
            return

        for path in self._image_paths:
            try:
                img = Image.open(path)
                img.thumbnail(PREVIEW_SIZE)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                lbl = ctk.CTkLabel(self._preview_frame, image=ctk_img, text="")
                lbl.pack(side="left", padx=4, pady=4)
            except Exception as exc:
                logger.warning(f"Preview failed: {exc}")

    # ── Schedule toggle ──

    def _toggle_schedule(self) -> None:
        state = "normal" if self._schedule_var.get() else "disabled"
        self._datetime_entry.configure(state=state)

    # ── Execute post ──

    def _do_post(self) -> None:
        text = self._text.get("1.0", "end").strip()
        if not text:
            self.app.notifier.warning("Input Error", "Please enter text")
            return

        scheduled_at = None
        if self._schedule_var.get():
            try:
                dt_str = self._datetime_entry.get().strip()
                scheduled_at = datetime.strptime(dt_str, "%Y/%m/%d %H:%M")
            except ValueError:
                self.app.notifier.warning(
                    "Date Error", "Enter date/time in YYYY/MM/DD HH:MM format"
                )
                return

        image_strs = [str(p) for p in self._image_paths] if self._image_paths else None
        self.app.bridge.create_post(text, image_strs, scheduled_at)
        self.app.notifier.info("Post", "Post submitted")
