"""画像使用履歴の管理.

指定ディレクトリ内の画像から未使用のものをランダムに選択し、
使用済み画像を追跡する。
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

from loguru import logger

# 対応拡張子
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# デフォルトの履歴保存先
DEFAULT_HISTORY_FILE = Path("config/image_history.json")


class ImageHistory:
    """画像使用履歴マネージャ.

    JSON ファイルでディレクトリごとの使用済みパスを永続化し、
    未使用画像のみをランダムに返す。
    """

    def __init__(self, history_file: Optional[Path] = None) -> None:
        self._file = history_file or DEFAULT_HISTORY_FILE
        self._used: dict[str, list[str]] = {}  # dir_key -> [filename, ...]
        self._load()

    # ── パブリック API ────────────────────────────────

    def pick_unused(self, directory: Path, count: int = 1) -> list[Path]:
        """ディレクトリから未使用画像をランダムに *count* 枚返す.

        Args:
            directory: 画像ディレクトリ
            count: 取得枚数

        Returns:
            選ばれた画像パスのリスト（足りなければ少なく返る）
        """
        unused = self._get_unused(directory)
        if not unused:
            logger.warning(f"未使用画像なし: {directory}")
            return []

        chosen = random.sample(unused, min(count, len(unused)))
        dir_key = self._dir_key(directory)
        self._used.setdefault(dir_key, [])
        for p in chosen:
            self._used[dir_key].append(p.name)
        self._save()

        logger.info(
            f"画像選択: {[p.name for p in chosen]}  "
            f"(残り {len(unused) - len(chosen)} 枚)"
        )
        return chosen

    def get_stats(self, directory: Path) -> tuple[int, int, int]:
        """統計情報を返す.

        Returns:
            (全画像数, 使用済み数, 未使用数)
        """
        all_images = self._scan(directory)
        used = self._used_set(directory)
        used_count = sum(1 for p in all_images if p.name in used)
        return len(all_images), used_count, len(all_images) - used_count

    def reset(self, directory: Path) -> None:
        """指定ディレクトリの使用履歴をリセットする."""
        dir_key = self._dir_key(directory)
        self._used.pop(dir_key, None)
        self._save()
        logger.info(f"使用履歴リセット: {directory}")

    def reset_all(self) -> None:
        """すべてのディレクトリの使用履歴をリセット."""
        self._used.clear()
        self._save()
        logger.info("全使用履歴リセット")

    def mark_used(self, directory: Path, filename: str) -> None:
        """手動で画像を使用済みにする."""
        dir_key = self._dir_key(directory)
        self._used.setdefault(dir_key, [])
        if filename not in self._used[dir_key]:
            self._used[dir_key].append(filename)
            self._save()

    def is_used(self, directory: Path, filename: str) -> bool:
        """画像が使用済みか判定."""
        return filename in self._used_set(directory)

    # ── 内部メソッド ──────────────────────────────────

    def _get_unused(self, directory: Path) -> list[Path]:
        """未使用画像のリストを取得."""
        all_images = self._scan(directory)
        used = self._used_set(directory)
        return [p for p in all_images if p.name not in used]

    @staticmethod
    def _scan(directory: Path) -> list[Path]:
        """ディレクトリ内の画像ファイルを列挙."""
        if not directory.is_dir():
            return []
        return sorted(
            p for p in directory.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )

    def _used_set(self, directory: Path) -> set[str]:
        dir_key = self._dir_key(directory)
        return set(self._used.get(dir_key, []))

    @staticmethod
    def _dir_key(directory: Path) -> str:
        """ディレクトリの正規化キー."""
        return str(directory.resolve())

    # ── 永続化 ────────────────────────────────────────

    def _load(self) -> None:
        if self._file.exists():
            try:
                with open(self._file, encoding="utf-8") as f:
                    self._used = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"履歴ファイル読み込み失敗: {e}")
                self._used = {}

    def _save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._file, "w", encoding="utf-8") as f:
            json.dump(self._used, f, indent=2, ensure_ascii=False)
