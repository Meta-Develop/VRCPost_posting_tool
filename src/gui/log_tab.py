"""ログビューアタブ.

アプリケーションのログをリアルタイムで表示する。
"""

from __future__ import annotations

from typing import ClassVar

from loguru import logger
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

MAX_LINES = 1000


class QtLogHandler(QObject):
    """loguru用のQtシグナルベースログハンドラ.

    スレッドセーフにGUIへログを転送する。
    """

    log_emitted = Signal(str, str)  # (formatted_message, level)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._sink_id: int | None = None

    def install(self) -> None:
        """loguruにシンクを登録する."""
        self._sink_id = logger.add(
            self._write,
            level="DEBUG",
            format="{time:HH:mm:ss} | {level: <8} | {message}",
        )

    def uninstall(self) -> None:
        """loguruからシンクを除去する."""
        if self._sink_id is not None:
            logger.remove(self._sink_id)
            self._sink_id = None

    def _write(self, message: str) -> None:
        """loguruから呼ばれるシンク関数."""
        record = message.record
        level = record["level"].name
        self.log_emitted.emit(str(message).rstrip("\n"), level)


class LogTab(QWidget):
    """ログビューアタブ."""

    LEVEL_COLORS: ClassVar[dict[str, QColor]] = {
        "DEBUG": QColor(160, 160, 160),
        "INFO": QColor(220, 220, 220),
        "WARNING": QColor(250, 200, 50),
        "ERROR": QColor(240, 80, 80),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._handler = QtLogHandler(self)
        self._current_filter: str = "ALL"
        self._setup_ui()
        self._connect_signals()
        self._handler.install()
        logger.debug("ログタブを初期化しました")

    # ------------------------------------------------------------------
    # UI構築
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """UIを構築."""
        layout = QVBoxLayout(self)

        # ─── ツールバー ─────────────────────────────────────
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("レベル:"))
        self._level_combo = QComboBox()
        self._level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        self._level_combo.setFixedWidth(120)
        toolbar.addWidget(self._level_combo)

        toolbar.addStretch()

        self._clear_btn = QPushButton("クリア")
        toolbar.addWidget(self._clear_btn)

        self._copy_btn = QPushButton("コピー")
        toolbar.addWidget(self._copy_btn)

        self._export_btn = QPushButton("エクスポート")
        toolbar.addWidget(self._export_btn)

        layout.addLayout(toolbar)

        # ─── ログ表示エリア ─────────────────────────────────
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setFont(QFont("Consolas", 10))
        self._log_view.setStyleSheet(
            "QTextEdit { background: #1e1e1e; color: #dcdcdc; }"
        )
        layout.addWidget(self._log_view)

    # ------------------------------------------------------------------
    # シグナル接続
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """シグナルを接続."""
        self._handler.log_emitted.connect(self._on_log)
        self._level_combo.currentTextChanged.connect(self._on_filter_changed)
        self._clear_btn.clicked.connect(self._clear)
        self._copy_btn.clicked.connect(self._copy_to_clipboard)
        self._export_btn.clicked.connect(self._export_to_file)

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------

    @Slot(str, str)
    def _on_log(self, message: str, level: str) -> None:
        """ログ行を追加する (スレッドセーフ)."""
        if not self._matches_filter(level):
            return

        color = self.LEVEL_COLORS.get(level, QColor(220, 220, 220))

        fmt = QTextCharFormat()
        fmt.setForeground(color)

        cursor = self._log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(message + "\n", fmt)

        self._trim_lines()
        self._auto_scroll()

    def _on_filter_changed(self, level_text: str) -> None:
        """フィルタ変更時の処理."""
        self._current_filter = level_text

    def _clear(self) -> None:
        """ログ表示をクリア."""
        self._log_view.clear()

    def _copy_to_clipboard(self) -> None:
        """表示中テキストをクリップボードへコピー."""
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._log_view.toPlainText())

    def _export_to_file(self) -> None:
        """ログをテキストファイルにエクスポート."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "ログをエクスポート",
            "application.log",
            "Log Files (*.log *.txt);;All Files (*)",
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._log_view.toPlainText())
                logger.info(f"ログをエクスポートしました: {path}")
            except OSError:
                logger.error(f"ログのエクスポートに失敗しました: {path}")

    # ------------------------------------------------------------------
    # ヘルパー
    # ------------------------------------------------------------------

    def _matches_filter(self, level: str) -> bool:
        """現在のフィルタにマッチするか判定."""
        if self._current_filter == "ALL":
            return True
        priority = ["DEBUG", "INFO", "WARNING", "ERROR"]
        try:
            return priority.index(level) >= priority.index(self._current_filter)
        except ValueError:
            return True

    def _trim_lines(self) -> None:
        """最大行数を超えたら古い行を削除."""
        doc = self._log_view.document()
        while doc.blockCount() > MAX_LINES:
            cursor = QTextCursor(doc.begin())
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.movePosition(
                QTextCursor.MoveOperation.NextBlock,
                QTextCursor.MoveMode.KeepAnchor,
            )
            cursor.removeSelectedText()

    def _auto_scroll(self) -> None:
        """最下部へ自動スクロール."""
        scrollbar = self._log_view.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())

    # ------------------------------------------------------------------
    # クリーンアップ
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """タブ破棄時にloguruシンクを除去する."""
        self._handler.uninstall()
