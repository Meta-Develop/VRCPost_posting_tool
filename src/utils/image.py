"""Image processing utilities.

Resize, thumbnail generation, etc. for post images.
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
    """Resize an image.

    Fits the image within the specified dimensions while preserving
    the aspect ratio.

    Args:
        image_path: Path to the source image.
        max_width: Maximum width.
        max_height: Maximum height.
        quality: JPEG quality (1-100).
        output_path: Output path (None to overwrite).

    Returns:
        Path to the saved image.
    """
    img = Image.open(image_path)
    original_size = img.size

    # No resize needed
    if img.width <= max_width and img.height <= max_height:
        if output_path:
            img.save(output_path, quality=quality)
            return output_path
        return image_path

    # Resize preserving aspect ratio
    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    save_path = output_path or image_path
    img.save(save_path, quality=quality)

    logger.info(f"Image resized: {original_size} -> {img.size} ({save_path.name})")
    return save_path


def create_thumbnail(
    image_path: Path,
    size: tuple[int, int] = (200, 200),
    output_path: Optional[Path] = None,
) -> Path:
    """Generate a thumbnail.

    Args:
        image_path: Path to the source image.
        size: Thumbnail size (width, height).
        output_path: Output path.

    Returns:
        Path to the thumbnail.
    """
    img = Image.open(image_path)
    img.thumbnail(size, Image.Resampling.LANCZOS)

    if output_path is None:
        stem = image_path.stem
        output_path = image_path.parent / f"{stem}_thumb{image_path.suffix}"

    img.save(output_path)
    logger.debug(f"Thumbnail created: {output_path.name}")
    return output_path


def validate_image(image_path: Path, max_size_kb: int = 5120) -> tuple[bool, str]:
    """Validate an image file.

    Args:
        image_path: Image path.
        max_size_kb: Max file size in KB.

    Returns:
        (valid, message) tuple.
    """
    if not image_path.exists():
        return False, f"File not found: {image_path}"

    # Size check
    file_size_kb = image_path.stat().st_size / 1024
    if file_size_kb > max_size_kb:
        return False, f"File too large: {file_size_kb:.0f}KB (limit: {max_size_kb}KB)"

    # Check if it can be opened as an image
    try:
        img = Image.open(image_path)
        img.verify()
    except Exception as e:
        return False, f"Invalid image file: {e}"

    # Format check
    suffix = image_path.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return False, f"Unsupported format: {suffix}"

    return True, "OK"
