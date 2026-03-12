"""Story tab (CustomTkinter).

Provides a UI for story image uploads.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk
from loguru import logger
from PIL import Image

if TYPE_CHECKING:
    from src.gui.main_window import App

PREVIEW_SIZE = (200, 200)


class StoryTab(ctk.CTkFrame):
    """Story tab."""

    def __init__(self, parent: ctk.CTkFrame, app: App) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._image_path: Path | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self, text="Story", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", pady=(0, 12))

        # Image selection
        sel_frame = ctk.CTkFrame(self, fg_color="transparent")
        sel_frame.pack(fill="x")
        ctk.CTkButton(
            sel_frame,
            text="Select Image",
            width=120,
            height=32,
            corner_radius=6,
            command=self._select_image,
        ).pack(side="left")
        self._path_label = ctk.CTkLabel(
            sel_frame, text="Not selected", text_color="gray", font=ctk.CTkFont(size=12)
        )
        self._path_label.pack(side="left", padx=12)

        # Preview
        self._preview_frame = ctk.CTkFrame(self, height=220, corner_radius=8)
        self._preview_frame.pack(fill="x", pady=(8, 12))
        self._preview_label = ctk.CTkLabel(
            self._preview_frame, text="No image", text_color="gray"
        )
        self._preview_label.pack(expand=True, pady=20)

        # Text
        ctk.CTkLabel(self, text="Text (optional)", font=ctk.CTkFont(size=13)).pack(
            anchor="w"
        )
        self._text = ctk.CTkTextbox(self, height=80, corner_radius=8)
        self._text.pack(fill="x", pady=(4, 12))

        # Upload button
        ctk.CTkButton(
            self,
            text="Upload Story",
            height=40,
            corner_radius=8,
            fg_color="#6366f1",
            hover_color="#818cf8",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._do_upload,
        ).pack(fill="x", pady=(8, 0))

    def _select_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Story Image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.gif *.webp *.bmp")],
        )
        if not path:
            return
        self._image_path = Path(path)
        self._path_label.configure(text=self._image_path.name)
        self._show_preview()

    def _show_preview(self) -> None:
        for w in self._preview_frame.winfo_children():
            w.destroy()
        if not self._image_path:
            return
        try:
            img = Image.open(self._image_path)
            img.thumbnail(PREVIEW_SIZE)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            ctk.CTkLabel(self._preview_frame, image=ctk_img, text="").pack(
                expand=True, pady=8
            )
        except Exception as exc:
            logger.warning(f"Preview failed: {exc}")

    def _do_upload(self) -> None:
        if not self._image_path:
            self.app.notifier.warning("Input Error", "Please select an image")
            return
        text = self._text.get("1.0", "end").strip() or None
        self.app.bridge.upload_story(str(self._image_path), text)
        self.app.notifier.info("Story", "Upload submitted")
