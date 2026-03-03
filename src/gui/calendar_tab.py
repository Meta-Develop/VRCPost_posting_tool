"""カレンダータブ (CustomTkinter).

月ごとのジョブを視覚的に確認できるカレンダー UI。
"""

from __future__ import annotations

import calendar
from datetime import date
from typing import TYPE_CHECKING

import customtkinter as ctk

from src.scheduler.jobs import ScheduledJob

if TYPE_CHECKING:
    from src.gui.main_window import App

DAY_NAMES = ["月", "火", "水", "木", "金", "土", "日"]
ACCENT = "#6366f1"


class CalendarTab(ctk.CTkFrame):
    """カレンダータブ."""

    def __init__(self, parent: ctk.CTkFrame, app: App) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        today = date.today()
        self._year = today.year
        self._month = today.month
        self._selected_date: date | None = None
        self._build_ui()
        self._render_month()

    # ── UI ──

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self, text="カレンダー", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", pady=(0, 8))

        # 左右: カレンダー + 詳細
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # カレンダー側
        cal_frame = ctk.CTkFrame(body, corner_radius=8)
        cal_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # ナビゲーション
        nav = ctk.CTkFrame(cal_frame, fg_color="transparent")
        nav.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(
            nav, text="◀", width=36, height=28, corner_radius=6,
            command=self._prev_month,
        ).pack(side="left")
        self._month_label = ctk.CTkLabel(
            nav, text="", font=ctk.CTkFont(size=15, weight="bold")
        )
        self._month_label.pack(side="left", expand=True)
        ctk.CTkButton(
            nav, text="▶", width=36, height=28, corner_radius=6,
            command=self._next_month,
        ).pack(side="right")

        # 曜日ヘッダー
        header = ctk.CTkFrame(cal_frame, fg_color="transparent")
        header.pack(fill="x", padx=8)
        for d in DAY_NAMES:
            ctk.CTkLabel(
                header, text=d, width=44, font=ctk.CTkFont(size=11),
                text_color="gray",
            ).pack(side="left", expand=True)

        # 日グリッド
        self._grid_frame = ctk.CTkFrame(cal_frame, fg_color="transparent")
        self._grid_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # 詳細パネル
        detail = ctk.CTkFrame(body, width=280, corner_radius=8)
        detail.pack(side="left", fill="y")
        detail.pack_propagate(False)

        self._detail_title = ctk.CTkLabel(
            detail, text="日付を選択", font=ctk.CTkFont(size=14, weight="bold")
        )
        self._detail_title.pack(pady=(12, 8))

        self._detail_scroll = ctk.CTkScrollableFrame(detail, fg_color="transparent")
        self._detail_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ── カレンダー描画 ──

    def _render_month(self) -> None:
        self._month_label.configure(text=f"{self._year}年 {self._month}月")

        for w in self._grid_frame.winfo_children():
            w.destroy()

        jobs = self.app.connector.get_jobs()
        job_dates = self._jobs_by_date(jobs)

        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdayscalendar(self._year, self._month)

        for row_idx, week in enumerate(weeks):
            row = ctk.CTkFrame(self._grid_frame, fg_color="transparent")
            row.pack(fill="x")
            for col_idx, day in enumerate(week):
                cell = ctk.CTkFrame(row, width=44, height=40, fg_color="transparent")
                cell.pack(side="left", expand=True, pady=1)
                cell.pack_propagate(False)

                if day == 0:
                    continue

                d = date(self._year, self._month, day)
                has_jobs = d in job_dates
                is_today = d == date.today()

                fg = ACCENT if is_today else ("gray25" if has_jobs else "transparent")
                tc = "white" if is_today else ("white" if has_jobs else "gray90")

                btn = ctk.CTkButton(
                    cell,
                    text=str(day),
                    width=40,
                    height=36,
                    corner_radius=6,
                    fg_color=fg,
                    hover_color="gray35",
                    text_color=tc,
                    font=ctk.CTkFont(size=12),
                    command=lambda dd=d: self._select_day(dd),
                )
                btn.pack(expand=True)

                # ジョブドット
                if has_jobs and not is_today:
                    dot = ctk.CTkFrame(cell, width=6, height=6, corner_radius=3, fg_color=ACCENT)
                    dot.place(relx=0.5, rely=0.9, anchor="center")

    # ── ナビゲーション ──

    def _prev_month(self) -> None:
        if self._month == 1:
            self._month = 12
            self._year -= 1
        else:
            self._month -= 1
        self._render_month()

    def _next_month(self) -> None:
        if self._month == 12:
            self._month = 1
            self._year += 1
        else:
            self._month += 1
        self._render_month()

    # ── 日付選択 ──

    def _select_day(self, d: date) -> None:
        self._selected_date = d
        self._detail_title.configure(text=d.strftime("%Y/%m/%d"))

        for w in self._detail_scroll.winfo_children():
            w.destroy()

        jobs = self.app.connector.get_jobs()
        day_jobs = [
            j for j in jobs if j.scheduled_at.date() == d
        ]

        if not day_jobs:
            ctk.CTkLabel(
                self._detail_scroll, text="ジョブなし", text_color="gray"
            ).pack(pady=20)
            return

        for j in day_jobs:
            card = ctk.CTkFrame(self._detail_scroll, corner_radius=6)
            card.pack(fill="x", pady=2)
            ctk.CTkLabel(
                card,
                text=f"{j.scheduled_at.strftime('%H:%M')}  {j.job_type.value}",
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(anchor="w", padx=8, pady=(6, 2))
            ctk.CTkLabel(
                card,
                text=f"{j.text[:40]}..." if len(j.text) > 40 else j.text,
                font=ctk.CTkFont(size=11),
                text_color="gray",
            ).pack(anchor="w", padx=8, pady=(0, 6))

    # ── ヘルパー ──

    @staticmethod
    def _jobs_by_date(jobs: list[ScheduledJob]) -> set[date]:
        return {j.scheduled_at.date() for j in jobs}

    def on_show(self) -> None:
        """タブ表示時にリフレッシュ."""
        self._render_month()
