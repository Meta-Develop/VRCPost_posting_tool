"""ログ設定.

loguruを使って構造化ログを出力する。
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

LOG_DIR = Path(__file__).parent.parent.parent / "logs"


def setup_logger(log_level: str = "DEBUG") -> None:
    """ロガーを初期化.

    Args:
        log_level: ログレベル (DEBUG, INFO, WARNING, ERROR)
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # デフォルトのハンドラを削除
    logger.remove()

    # コンソール出力
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )

    # ファイル出力
    logger.add(
        LOG_DIR / "app.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
    )

    # エラー専用ログ
    logger.add(
        LOG_DIR / "error.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="5 MB",
        retention="30 days",
        encoding="utf-8",
    )

    logger.info("ロガーを初期化しました")
