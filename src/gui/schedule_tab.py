"""スケジュールタブ (CustomTkinter).

登録済みジョブの一覧表示・キャンセル操作を提供する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from src.scheduler.jobs import JobStatus

if TYPE_CHECKING:
    from src.gui.main_window import App

STATUS_COLORS = {
    JobStatus.PENDING: "#3b82f6",
    JobStatus.RUNNING: "#f59e0b",
    JobStatus.COMPLETED: "#22c55e",
    JobStatus.FAILED: "#ef4444",
    JobStatus.CANCELLED: "#6b7280",
}


class ScheduleTab(ctk.CTkFrame):
    """スケジュールタブ."""

    def __init__(self, parent: ctk.CTkFrame, app: App) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._build_ui()

    def _build_ui(self) -> None:
        # ヘッダー
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            header, text="スケジュール", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="更新",
            width=70,
            height=28,
            corner_radius=6,
            command=self._refresh,
        ).pack(side="right")

        self._count_label = ctk.CTkLabel(
            header, text="", font=ctk.CTkFont(size=12), text_color="gray"
        )
        self._count_label.pack(side="right", padx=12)

        # テーブルヘッダー
        th = ctk.CTkFrame(self, corner_radius=0, height=30)
        th.pack(fill="x")
        th.pack_propagate(False)
        cols = [("ID", 80), ("種類", 70), ("日時", 140), ("テキスト", 0), ("状態", 80)]
        for label, w in cols:
            kw: dict = {"text": label, "font": ctk.CTkFont(size=11, weight="bold")}
            if w:
                kw["width"] = w
            lbl = ctk.CTkLabel(th, **kw)
            if w:
                lbl.pack(side="left", padx=4)
            else:
                lbl.pack(side="left", expand=True, fill="x", padx=4)

        # スクロール可能リスト
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, pady=(2, 0))

    # ── リフレッシュ ──

    def _refresh(self) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()

        jobs = self.app.connector.get_jobs()
        self._count_label.configure(text=f"{len(jobs)} 件")

        if not jobs:
            ctk.CTkLabel(
                self._scroll, text="ジョブなし", text_color="gray"
            ).pack(pady=30)
            return

        for job in sorted(jobs, key=lambda j: j.scheduled_at, reverse=True):
            row = ctk.CTkFrame(self._scroll, corner_radius=6, height=36)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            ctk.CTkLabel(
                row, text=job.id, width=80, font=ctk.CTkFont(size=11)
            ).pack(side="left", padx=4)
            ctk.CTkLabel(
                row, text=job.job_type.value, width=70, font=ctk.CTkFont(size=11)
            ).pack(side="left", padx=4)
            ctk.CTkLabel(
                row, text=job.display_time, width=140, font=ctk.CTkFont(size=11)
            ).pack(side="left", padx=4)
            ctk.CTkLabel(
                row,
                text=job.text[:30] if job.text else "",
                font=ctk.CTkFont(size=11),
                anchor="w",
            ).pack(side="left", expand=True, fill="x", padx=4)

            status_color = STATUS_COLORS.get(job.status, "gray")
            ctk.CTkLabel(
                row,
                text=job.display_status,
                width=60,
                font=ctk.CTkFont(size=11),
                text_color=status_color,
            ).pack(side="left", padx=4)

            if job.status == JobStatus.PENDING:
                ctk.CTkButton(
                    row,
                    text="取消",
                    width=44,
                    height=24,
                    corner_radius=4,
                    fg_color="#ef4444",
                    hover_color="#dc2626",
                    font=ctk.CTkFont(size=10),
                    command=lambda jid=job.id: self._cancel_job(jid),
                ).pack(side="left", padx=4)

    def _cancel_job(self, job_id: str) -> None:
        self.app.connector.remove_job(job_id)
        self.app.notifier.info("キャンセル", f"ジョブ {job_id} をキャンセルしました")
        self._refresh()

    def on_show(self) -> None:
        """タブ表示時に自動更新."""
        self._refresh()
