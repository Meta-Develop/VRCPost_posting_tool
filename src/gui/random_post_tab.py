"""ランダム投稿タブ (CustomTkinter).

指定フォルダから未使用画像をランダム選択して投稿する。
自動投稿タイマー、シャッフル/スキップ、残り枚数アラート付き。
"""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk
from loguru import logger
from PIL import Image

from src.utils.image_history import ImageHistory

if TYPE_CHECKING:
    from src.gui.main_window import App

PREVIEW_SIZE = (180, 180)
LOW_IMAGE_THRESHOLD = 5


class RandomPostTab(ctk.CTkFrame):
    """ランダム投稿タブ."""

    def __init__(self, parent: ctk.CTkFrame, app: App) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._history = ImageHistory()
        self._directory: Path | None = None
        self._current_images: list[Path] = []
        self._auto_timer_id: str | None = None
        self._build_ui()

    # ── UI 構築 ──

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self, text="ランダム投稿", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", pady=(0, 12))

        # フォルダ選択
        folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        folder_frame.pack(fill="x")
        ctk.CTkButton(
            folder_frame,
            text="フォルダを選択",
            width=120,
            height=32,
            corner_radius=6,
            command=self._select_folder,
        ).pack(side="left")
        self._folder_label = ctk.CTkLabel(
            folder_frame, text="未選択", text_color="gray", font=ctk.CTkFont(size=12)
        )
        self._folder_label.pack(side="left", padx=12)

        # 統計情報
        self._stats_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), text_color="gray"
        )
        self._stats_label.pack(anchor="w", pady=(4, 8))

        # プレビュー + 操作
        mid_frame = ctk.CTkFrame(self, fg_color="transparent")
        mid_frame.pack(fill="x", pady=(0, 8))

        self._preview_frame = ctk.CTkFrame(mid_frame, width=200, height=200, corner_radius=8)
        self._preview_frame.pack(side="left", padx=(0, 12))
        self._preview_frame.pack_propagate(False)
        self._no_img_label = ctk.CTkLabel(
            self._preview_frame, text="画像なし", text_color="gray"
        )
        self._no_img_label.pack(expand=True)

        ctrl_frame = ctk.CTkFrame(mid_frame, fg_color="transparent")
        ctrl_frame.pack(side="left", fill="y")

        ctk.CTkButton(
            ctrl_frame, text="シャッフル", width=100, height=30, corner_radius=6,
            command=self._shuffle,
        ).pack(pady=2)
        ctk.CTkButton(
            ctrl_frame, text="スキップ", width=100, height=30, corner_radius=6,
            fg_color="gray40", command=self._skip,
        ).pack(pady=2)

        # 枚数
        count_frame = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        count_frame.pack(pady=(8, 2))
        ctk.CTkLabel(count_frame, text="枚数:", font=ctk.CTkFont(size=12)).pack(side="left")
        self._count_var = ctk.StringVar(value="1")
        ctk.CTkOptionMenu(
            count_frame,
            values=["1", "2", "3", "4"],
            variable=self._count_var,
            width=60,
        ).pack(side="left", padx=4)

        # テキスト
        ctk.CTkLabel(self, text="テキスト（任意）", font=ctk.CTkFont(size=13)).pack(
            anchor="w"
        )
        self._text = ctk.CTkTextbox(self, height=60, corner_radius=8)
        self._text.pack(fill="x", pady=(4, 8))

        # 自動投稿セクション
        auto_frame = ctk.CTkFrame(self, corner_radius=8)
        auto_frame.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            auto_frame, text="自動投稿", font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=12, pady=(8, 4))

        row = ctk.CTkFrame(auto_frame, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 8))

        self._auto_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            row, text="有効", variable=self._auto_var, command=self._toggle_auto
        ).pack(side="left")

        ctk.CTkLabel(row, text="間隔(分):", font=ctk.CTkFont(size=12)).pack(
            side="left", padx=(16, 4)
        )
        self._interval_entry = ctk.CTkEntry(row, width=60, placeholder_text="30")
        self._interval_entry.pack(side="left")

        ctk.CTkLabel(row, text="残り警告:", font=ctk.CTkFont(size=12)).pack(
            side="left", padx=(16, 4)
        )
        self._threshold_entry = ctk.CTkEntry(row, width=60, placeholder_text="5")
        self._threshold_entry.pack(side="left")

        # ボタン行
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x")
        ctk.CTkButton(
            btn_frame,
            text="投稿する",
            height=40,
            corner_radius=8,
            fg_color="#6366f1",
            hover_color="#818cf8",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._do_post,
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(
            btn_frame,
            text="履歴リセット",
            height=40,
            corner_radius=8,
            fg_color="gray40",
            command=self._reset_history,
        ).pack(side="left", width=120)

    # ── フォルダ ──

    def _select_folder(self) -> None:
        path = filedialog.askdirectory(title="画像フォルダを選択")
        if not path:
            return
        self._directory = Path(path)
        self._folder_label.configure(text=str(self._directory))
        self._refresh_stats()
        self._shuffle()

    # ── 統計 ──

    def _refresh_stats(self) -> None:
        if not self._directory:
            self._stats_label.configure(text="")
            return
        total, used, unused = self._history.get_stats(self._directory)
        self._stats_label.configure(
            text=f"全 {total} 枚 / 使用済 {used} 枚 / 残り {unused} 枚"
        )

        threshold = self._get_threshold()
        if unused <= threshold and unused > 0:
            self.app.notifier.warning(
                "画像残りわずか",
                f"{self._directory.name}: 残り {unused} 枚 (閾値: {threshold})",
            )

    def _get_threshold(self) -> int:
        try:
            return int(self._threshold_entry.get())
        except ValueError:
            return LOW_IMAGE_THRESHOLD

    # ── シャッフル / スキップ ──

    def _shuffle(self) -> None:
        if not self._directory:
            return
        count = int(self._count_var.get())
        self._current_images = self._history.pick_unused(self._directory, count)
        self._show_preview()
        self._refresh_stats()

    def _skip(self) -> None:
        self._shuffle()

    def _show_preview(self) -> None:
        for w in self._preview_frame.winfo_children():
            w.destroy()
        if not self._current_images:
            ctk.CTkLabel(
                self._preview_frame, text="画像なし", text_color="gray"
            ).pack(expand=True)
            return
        try:
            img = Image.open(self._current_images[0])
            img.thumbnail(PREVIEW_SIZE)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            ctk.CTkLabel(self._preview_frame, image=ctk_img, text="").pack(
                expand=True
            )
        except Exception as exc:
            logger.warning(f"プレビュー失敗: {exc}")

    # ── 自動投稿 ──

    def _toggle_auto(self) -> None:
        if self._auto_var.get():
            self._start_auto()
        else:
            self._stop_auto()

    def _start_auto(self) -> None:
        try:
            minutes = int(self._interval_entry.get())
        except ValueError:
            minutes = 30
        ms = minutes * 60 * 1000
        logger.info(f"自動投稿開始: {minutes}分間隔")
        self._auto_tick(ms)

    def _auto_tick(self, ms: int) -> None:
        if not self._auto_var.get():
            return
        self._do_post()
        self._auto_timer_id = self.after(ms, self._auto_tick, ms)

    def _stop_auto(self) -> None:
        if self._auto_timer_id:
            self.after_cancel(self._auto_timer_id)
            self._auto_timer_id = None
        logger.info("自動投稿停止")

    # ── 投稿実行 ──

    def _do_post(self) -> None:
        if not self._directory:
            self.app.notifier.warning("入力エラー", "フォルダを選択してください")
            return

        # シャッフル済みでなければ取得
        if not self._current_images:
            count = int(self._count_var.get())
            self._current_images = self._history.pick_unused(self._directory, count)

        if not self._current_images:
            self.app.notifier.warning("画像切れ", "未使用の画像がありません")
            self._stop_auto()
            return

        text = self._text.get("1.0", "end").strip()
        image_strs = [str(p) for p in self._current_images]
        self.app.bridge.create_post(text, image_strs)
        self.app.notifier.info("ランダム投稿", f"{len(image_strs)} 枚投稿しました")

        self._current_images.clear()
        self._refresh_stats()
        self._show_preview()

    # ── リセット ──

    def _reset_history(self) -> None:
        if self._directory:
            self._history.reset(self._directory)
            self._refresh_stats()
            self.app.notifier.info("リセット", "使用履歴をリセットしました")
