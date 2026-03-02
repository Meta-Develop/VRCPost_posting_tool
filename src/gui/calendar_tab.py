"""カレンダータブ.

予約投稿をカレンダー形式で可視化する。
月ごとにマスを描画し、予約がある日はドットや件数で表示する。
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QCalendarWidget,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import AppSettings

if TYPE_CHECKING:
    from src.scheduler.connector import SchedulerConnector


class _JobCalendar(QCalendarWidget):
    """予約ジョブをドット表示するカレンダーウィジェット."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._job_dates: dict[date, int] = {}  # date -> ジョブ件数

        # 見た目調整
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setNavigationBarVisible(True)

    def set_job_dates(self, job_dates: dict[date, int]) -> None:
        """ジョブがある日付と件数をセット."""
        self._job_dates = job_dates
        self.updateCells()

    def paintCell(self, painter: QPainter, rect, date_val: date) -> None:  # noqa: N802
        """セルを描画（ジョブがある日にはドットを表示）."""
        super().paintCell(painter, rect, date_val)

        count = self._job_dates.get(date_val, 0)
        if count == 0:
            return

        # ドット描画
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        dot_radius = 4
        dot_x = rect.center().x()
        dot_y = rect.bottom() - dot_radius - 2

        # 件数に応じた色
        if count >= 3:
            color = QColor("#ef4444")  # 赤 (3件以上)
        elif count == 2:
            color = QColor("#f59e0b")  # オレンジ
        else:
            color = QColor("#6366f1")  # 紫 (1件)

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(dot_x - dot_radius, dot_y - dot_radius,
                            dot_radius * 2, dot_radius * 2)

        # 件数が2以上なら数字
        if count >= 2:
            painter.setPen(QColor("white"))
            font = QFont()
            font.setPixelSize(8)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                dot_x - dot_radius, dot_y - dot_radius,
                dot_radius * 2, dot_radius * 2,
                Qt.AlignmentFlag.AlignCenter, str(count),
            )

        painter.restore()


class CalendarTab(QWidget):
    """カレンダービュータブ.

    予約投稿をカレンダー上で俯瞰表示し、
    日付クリックでその日の予約一覧を確認できる。
    """

    # 日付選択シグナル
    date_selected = Signal(object)  # date

    def __init__(
        self,
        settings: AppSettings,
        connector: SchedulerConnector | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self._connector = connector

        self._setup_ui()

        # 60秒ごとに自動更新
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh)
        self._refresh_timer.start(60_000)

        self._refresh()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── 左: カレンダー ───────────────────────────
        left = QVBoxLayout()

        cal_group = QGroupBox("スケジュールカレンダー")
        cal_layout = QVBoxLayout(cal_group)

        self._calendar = _JobCalendar()
        self._calendar.clicked.connect(self._on_date_clicked)
        cal_layout.addWidget(self._calendar)

        # 凡例
        legend_layout = QHBoxLayout()
        for color, label in [
            ("#6366f1", "1件"), ("#f59e0b", "2件"), ("#ef4444", "3件+"),
        ]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 14px;")
            legend_layout.addWidget(dot)
            legend_layout.addWidget(QLabel(label))
        legend_layout.addStretch()
        cal_layout.addLayout(legend_layout)

        # 今日ボタン
        btn_row = QHBoxLayout()
        today_btn = QPushButton("今日")
        today_btn.clicked.connect(self._go_today)
        btn_row.addWidget(today_btn)

        refresh_btn = QPushButton("更新")
        refresh_btn.clicked.connect(self._refresh)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        cal_layout.addLayout(btn_row)

        left.addWidget(cal_group)
        layout.addLayout(left, 1)

        # ── 右: 選択日の予約一覧 ─────────────────────
        right = QVBoxLayout()

        detail_group = QGroupBox("選択日の予約")
        detail_layout = QVBoxLayout(detail_group)

        self._date_label = QLabel("")
        self._date_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        detail_layout.addWidget(self._date_label)

        self._detail_table = QTableWidget()
        self._detail_table.setColumnCount(4)
        self._detail_table.setHorizontalHeaderLabels(["時刻", "種類", "テキスト", "状態"])
        self._detail_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._detail_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        from PySide6.QtWidgets import QHeaderView
        header = self._detail_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        detail_layout.addWidget(self._detail_table)

        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        detail_layout.addWidget(self._summary_label)

        right.addWidget(detail_group)
        layout.addLayout(right, 1)

    # ── データ更新 ────────────────────────────────────

    def _refresh(self) -> None:
        """ジョブ情報をカレンダーに反映."""
        job_dates: dict[date, int] = {}

        if self._connector:
            for job in self._connector.get_jobs():
                d = job.scheduled_at.date()
                job_dates[d] = job_dates.get(d, 0) + 1

        self._calendar.set_job_dates(job_dates)

        # 現在選択中の日を再表示
        selected = self._calendar.selectedDate().toPython()
        self._show_day_detail(selected)

        logger.debug(f"カレンダー更新: {len(job_dates)} 日にジョブあり")

    def refresh(self) -> None:
        """外部から呼び出し可能な更新."""
        self._refresh()

    # ── 日付クリック ──────────────────────────────────

    def _on_date_clicked(self, qdate) -> None:
        d = qdate.toPython()
        self._show_day_detail(d)
        self.date_selected.emit(d)

    def _show_day_detail(self, d: date) -> None:
        """選択日の予約一覧を右パネルに表示."""
        self._date_label.setText(d.strftime("%Y年%m月%d日 (%a)"))
        self._detail_table.setRowCount(0)

        if not self._connector:
            self._summary_label.setText("スケジューラー未接続")
            return

        day_jobs = [
            job for job in self._connector.get_jobs()
            if job.scheduled_at.date() == d
        ]
        day_jobs.sort(key=lambda j: j.scheduled_at)

        for job in day_jobs:
            row = self._detail_table.rowCount()
            self._detail_table.insertRow(row)
            self._detail_table.setItem(
                row, 0, QTableWidgetItem(job.scheduled_at.strftime("%H:%M")),
            )
            type_label = "投稿" if job.job_type.value == "post" else "ストーリー"
            self._detail_table.setItem(row, 1, QTableWidgetItem(type_label))
            self._detail_table.setItem(row, 2, QTableWidgetItem(job.text[:40]))
            self._detail_table.setItem(row, 3, QTableWidgetItem(job.display_status))

        self._summary_label.setText(f"予約: {len(day_jobs)} 件")

    def _go_today(self) -> None:
        today = date.today()
        from PySide6.QtCore import QDate
        self._calendar.setSelectedDate(QDate(today.year, today.month, today.day))
        self._show_day_detail(today)
