"""Image uploads: validate with Pillow, store as WebP under MEDIA_ROOT.

Browsers often send an incorrect or empty Content-Type; we trust decoded pixels
only. The only host coupling is ``settings.MEDIA_ROOT`` and a caller-supplied
``media_subpath``.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from PIL import Image

_MAX_BYTES = 5 * 1024 * 1024

# Raster formats Pillow can reliably transcode to WebP (SVG and similar are excluded).
_ALLOWED_PIL_FORMATS = frozenset(
    {"JPEG", "PNG", "GIF", "WEBP", "BMP", "TIFF", "MPO", "ICO", "AVIF"}
)


def _prepare_image_for_webp(img: Image.Image) -> Image.Image:
    if img.mode == "RGBA":
        return img
    if img.mode == "LA":
        return img.convert("RGBA")
    if img.mode == "P":
        if "transparency" in img.info:
            return img.convert("RGBA")
        return img.convert("RGB")
    if img.mode == "CMYK":
        return img.convert("RGB")
    if img.mode == "RGB":
        return img
    if img.mode == "L":
        return img.convert("RGB")
    return img.convert("RGB")


def save_image_bytes_as_webp(raw: bytes, *, media_subpath: str = "uploads") -> str:
    """
    Decode raster bytes with Pillow, write lossy WebP under MEDIA_ROOT.

    Returns path relative to media root (POSIX), e.g. ``uploads/2026/03/ab12cd34ef56.webp``.
    """
    if len(raw) > _MAX_BYTES:
        raise ValueError("Image is too large.")

    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        raise ValueError("Invalid or corrupted image.") from None

    fmt = (img.format or "").upper()
    if fmt not in _ALLOWED_PIL_FORMATS:
        raise ValueError("Unsupported image type. Use a common raster format (PNG, JPEG, WebP, GIF, etc.).")

    if getattr(img, "n_frames", 1) > 1:
        img.seek(0)

    img = _prepare_image_for_webp(img)

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=88, method=6)
    webp_bytes = buf.getvalue()

    date_part = timezone.now().strftime("%Y/%m")
    rel_dir = Path(media_subpath) / date_part
    filename = f"{uuid.uuid4().hex[:12]}.webp"
    full_path = Path(settings.MEDIA_ROOT) / rel_dir / filename
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(webp_bytes)
    return f"{rel_dir.as_posix()}/{filename}"


def save_upload_as_webp(uploaded_file, *, media_subpath: str = "uploads") -> str:
    """
    Read upload, verify with Pillow, write lossy WebP under MEDIA_ROOT.

    Returns path relative to media root (POSIX), e.g. ``uploads/2026/03/ab12cd34ef56.webp``.
    """
    if getattr(uploaded_file, "size", None) and uploaded_file.size > _MAX_BYTES:
        raise ValueError("Image is too large.")

    raw = uploaded_file.read()
    return save_image_bytes_as_webp(raw, media_subpath=media_subpath)
