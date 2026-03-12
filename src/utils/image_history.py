"""Image usage history management.

Randomly select unused images from a directory and
track which images have been used.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

from loguru import logger

# Supported extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# Default history file
DEFAULT_HISTORY_FILE = Path("config/image_history.json")


class ImageHistory:
    """Image usage history manager.

    Persists per-directory used image paths in a JSON file
    and returns only unused images at random.
    """

    def __init__(self, history_file: Optional[Path] = None) -> None:
        self._file = history_file or DEFAULT_HISTORY_FILE
        self._used: dict[str, list[str]] = {}  # dir_key -> [filename, ...]
        self._load()

    # ── Public API ─────────────────────────────────

    def pick_unused(self, directory: Path, count: int = 1) -> list[Path]:
        """Return *count* random unused images from the directory.

        Args:
            directory: Image directory.
            count: Number of images to pick.

        Returns:
            List of chosen image paths (may be shorter if insufficient).
        """
        unused = self._get_unused(directory)
        if not unused:
            logger.warning(f"No unused images: {directory}")
            return []

        chosen = random.sample(unused, min(count, len(unused)))
        dir_key = self._dir_key(directory)
        self._used.setdefault(dir_key, [])
        for p in chosen:
            self._used[dir_key].append(p.name)
        self._save()

        logger.info(
            f"Images selected: {[p.name for p in chosen]}  "
            f"({len(unused) - len(chosen)} remaining)"
        )
        return chosen

    def get_stats(self, directory: Path) -> tuple[int, int, int]:
        """Return usage statistics.

        Returns:
            (total, used, unused)
        """
        all_images = self._scan(directory)
        used = self._used_set(directory)
        used_count = sum(1 for p in all_images if p.name in used)
        return len(all_images), used_count, len(all_images) - used_count

    def reset(self, directory: Path) -> None:
        """Reset usage history for a directory."""
        dir_key = self._dir_key(directory)
        self._used.pop(dir_key, None)
        self._save()
        logger.info(f"Usage history reset: {directory}")

    def reset_all(self) -> None:
        """Reset usage history for all directories."""
        self._used.clear()
        self._save()
        logger.info("All usage history reset")

    def mark_used(self, directory: Path, filename: str) -> None:
        """Manually mark an image as used."""
        dir_key = self._dir_key(directory)
        self._used.setdefault(dir_key, [])
        if filename not in self._used[dir_key]:
            self._used[dir_key].append(filename)
            self._save()

    def is_used(self, directory: Path, filename: str) -> bool:
        """Check if an image has been used."""
        return filename in self._used_set(directory)

    # ── Internal ───────────────────────────────────

    def _get_unused(self, directory: Path) -> list[Path]:
        """Get unused images."""
        all_images = self._scan(directory)
        used = self._used_set(directory)
        return [p for p in all_images if p.name not in used]

    @staticmethod
    def _scan(directory: Path) -> list[Path]:
        """List image files in a directory."""
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
        """Normalized directory key."""
        return str(directory.resolve())

    # ── Persistence ────────────────────────────────

    def _load(self) -> None:
        if self._file.exists():
            try:
                with open(self._file, encoding="utf-8") as f:
                    self._used = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load history file: {e}")
                self._used = {}

    def _save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._file, "w", encoding="utf-8") as f:
            json.dump(self._used, f, indent=2, ensure_ascii=False)
