"""投稿タブ (CustomTkinter).

テキスト入力・画像選択・予約投稿の UI を提供する。
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
    """投稿タブ."""

    def __init__(self, parent: ctk.CTkFrame, app: App) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._image_paths: list[Path] = []
        self._build_ui()

    # ── UI 構築 ──

    def _build_ui(self) -> None:
        # ヘッダー
        ctk.CTkLabel(
            self, text="投稿作成", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", pady=(0, 12))

        # テキスト入力
        ctk.CTkLabel(self, text="テキスト", font=ctk.CTkFont(size=13)).pack(anchor="w")
        self._text = ctk.CTkTextbox(self, height=120, corner_radius=8)
        self._text.pack(fill="x", pady=(4, 12))

        # 画像セクション
        img_header = ctk.CTkFrame(self, fg_color="transparent")
        img_header.pack(fill="x")
        ctk.CTkLabel(
            img_header, text="画像 (最大4枚)", font=ctk.CTkFont(size=13)
        ).pack(side="left")
        ctk.CTkButton(
            img_header,
            text="画像を追加",
            width=100,
            height=28,
            corner_radius=6,
            command=self._add_images,
        ).pack(side="right")
        ctk.CTkButton(
            img_header,
            text="クリア",
            width=60,
            height=28,
            corner_radius=6,
            fg_color="gray40",
            command=self._clear_images,
        ).pack(side="right", padx=(0, 6))

        # 画像プレビュー
        self._preview_frame = ctk.CTkFrame(self, height=140, corner_radius=8)
        self._preview_frame.pack(fill="x", pady=(4, 12))
        self._preview_label = ctk.CTkLabel(
            self._preview_frame, text="画像なし", text_color="gray"
        )
        self._preview_label.pack(expand=True)

        # 予約投稿
        sched_frame = ctk.CTkFrame(self, fg_color="transparent")
        sched_frame.pack(fill="x", pady=(0, 12))
        self._schedule_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            sched_frame,
            text="予約投稿",
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

        # 投稿ボタン
        ctk.CTkButton(
            self,
            text="投稿する",
            height=40,
            corner_radius=8,
            fg_color="#6366f1",
            hover_color="#818cf8",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._do_post,
        ).pack(fill="x", pady=(8, 0))

    # ── 画像操作 ──

    def _add_images(self) -> None:
        files = filedialog.askopenfilenames(
            title="画像を選択",
            filetypes=[("画像", "*.jpg *.jpeg *.png *.gif *.webp *.bmp")],
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
                self._preview_frame, text="画像なし", text_color="gray"
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
                logger.warning(f"プレビュー失敗: {exc}")

    # ── 予約切替 ──

    def _toggle_schedule(self) -> None:
        state = "normal" if self._schedule_var.get() else "disabled"
        self._datetime_entry.configure(state=state)

    # ── 投稿実行 ──

    def _do_post(self) -> None:
        text = self._text.get("1.0", "end").strip()
        if not text:
            self.app.notifier.warning("入力エラー", "テキストを入力してください")
            return

        scheduled_at = None
        if self._schedule_var.get():
            try:
                dt_str = self._datetime_entry.get().strip()
                scheduled_at = datetime.strptime(dt_str, "%Y/%m/%d %H:%M")
            except ValueError:
                self.app.notifier.warning(
                    "日時エラー", "日時を YYYY/MM/DD HH:MM 形式で入力してください"
                )
                return

        image_strs = [str(p) for p in self._image_paths] if self._image_paths else None
        self.app.bridge.create_post(text, image_strs, scheduled_at)
        self.app.notifier.info("投稿", "投稿を送信しました")
