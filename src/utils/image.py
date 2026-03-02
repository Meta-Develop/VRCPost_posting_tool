"""画像処理ユーティリティ.

投稿用画像のリサイズ、サムネイル生成等を行う。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger
from PIL import Image


def resize_image(
    image_path: Path,
    max_width: int = 1920,
    max_height: int = 1920,
    quality: int = 85,
    output_path: Optional[Path] = None,
) -> Path:
    """画像をリサイズ.

    アスペクト比を保持しながら指定サイズ以内に収める。

    Args:
        image_path: 元画像のパス
        max_width: 最大幅
        max_height: 最大高さ
        quality: JPEG品質 (1-100)
        output_path: 出力先パス（Noneの場合は上書き）

    Returns:
        保存先のパス
    """
    img = Image.open(image_path)
    original_size = img.size

    # リサイズ不要ならそのまま返す
    if img.width <= max_width and img.height <= max_height:
        if output_path:
            img.save(output_path, quality=quality)
            return output_path
        return image_path

    # アスペクト比を保ってリサイズ
    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    save_path = output_path or image_path
    img.save(save_path, quality=quality)

    logger.info(f"画像をリサイズ: {original_size} -> {img.size} ({save_path.name})")
    return save_path


def create_thumbnail(
    image_path: Path,
    size: tuple[int, int] = (200, 200),
    output_path: Optional[Path] = None,
) -> Path:
    """サムネイル画像を生成.

    Args:
        image_path: 元画像のパス
        size: サムネイルサイズ (width, height)
        output_path: 出力先パス

    Returns:
        サムネイルのパス
    """
    img = Image.open(image_path)
    img.thumbnail(size, Image.Resampling.LANCZOS)

    if output_path is None:
        stem = image_path.stem
        output_path = image_path.parent / f"{stem}_thumb{image_path.suffix}"

    img.save(output_path)
    logger.debug(f"サムネイル生成: {output_path.name}")
    return output_path


def validate_image(image_path: Path, max_size_kb: int = 5120) -> tuple[bool, str]:
    """画像のバリデーション.

    Args:
        image_path: 画像パス
        max_size_kb: 最大ファイルサイズ(KB)

    Returns:
        (valid, message) のタプル
    """
    if not image_path.exists():
        return False, f"ファイルが存在しません: {image_path}"

    # サイズチェック
    file_size_kb = image_path.stat().st_size / 1024
    if file_size_kb > max_size_kb:
        return False, f"ファイルサイズが大きすぎます: {file_size_kb:.0f}KB (上限: {max_size_kb}KB)"

    # 画像として開けるかチェック
    try:
        img = Image.open(image_path)
        img.verify()
    except Exception as e:
        return False, f"画像ファイルが不正です: {e}"

    # 対応フォーマットチェック
    suffix = image_path.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return False, f"未対応のフォーマットです: {suffix}"

    return True, "OK"
