"""Responsive WebP variants of media images, made once and cached for a year.

A logo uploaded at 512 px and drawn in a 48 px box costs every visitor the difference,
and a PNG costs more than the same pixels as WebP. Lighthouse reports both under
"Improve image delivery". ``{% media_img %}`` fixes it at the one place an ``<img>`` is
written: given the box it will be drawn in, it serves a WebP at that width and at twice
that width (``srcset`` 1x/2x), keeping the ``width``/``height`` that reserve the box.

**Where variants live.** Beside the source, under a ``_v/`` directory, named
``<stem>.<signature>.<width>w.webp``. The signature is taken from the source's size and
modification time, so replacing a file produces new names and a variant can be served
with an immutable one-year lifetime (``cache_control_for``). A variant is made on first
use and written atomically, so two workers rendering the same page cannot leave half a
file. No upscaling: a source narrower than the requested width keeps its own width.

**What passes through untouched.** Anything that is not a raster file under
``MEDIA_ROOT``: a static asset, an SVG, an external URL, a missing file, or a path that
resolves outside the media root. Those keep their own ``src`` and get no ``srcset``.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from django.conf import settings

from ..config import frontend_setting

RASTER_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})
DENSITIES = (1, 2)


def _source(url: str) -> tuple[Path, Path] | None:
    media_url = settings.MEDIA_URL or ""
    path = urlsplit(url or "").path
    if not media_url or not path.startswith(media_url):
        return None
    root = Path(settings.MEDIA_ROOT).resolve()
    candidate = (root / unquote(path[len(media_url):])).resolve()
    if root not in candidate.parents or candidate.suffix.lower() not in RASTER_SUFFIXES:
        return None
    return (root, candidate) if candidate.is_file() else None


def variant_url(url: str, width: int) -> str | None:
    found = _source(url)
    if found is None:
        return None
    root, source = found
    conf = frontend_setting("media_variants")
    stat = source.stat()
    signature = hashlib.sha1(f"{stat.st_size}:{stat.st_mtime_ns}:{conf['quality']}".encode()).hexdigest()[:10]
    target = source.parent / conf["dir"] / f"{source.stem}.{signature}.{width}w.webp"
    if not target.is_file() and not _render(source, target, width, conf["quality"]):
        return None
    return settings.MEDIA_URL + quote(target.relative_to(root).as_posix())


def _render(source: Path, target: Path, width: int, quality: int) -> bool:
    tmp = None
    try:
        from PIL import Image

        with Image.open(source) as image:
            image.load()
            has_alpha = image.mode in ("RGBA", "LA", "P") or "transparency" in image.info
            frame = image.convert("RGBA" if has_alpha else "RGB")
        if frame.width > width:
            frame = frame.resize((width, max(1, round(frame.height * width / frame.width))), Image.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
        os.close(fd)
        frame.save(tmp, "WEBP", quality=quality, method=6)
        os.replace(tmp, target)
        return True
    except Exception:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
        return False


def img_attrs(url: str, width, height) -> dict:
    """``src``/``srcset``/``width``/``height`` for an image drawn in a ``width`` box."""
    attrs = {"src": url, "width": width, "height": height}
    try:
        box = int(width)
    except (TypeError, ValueError):
        return attrs
    variants = [(density, variant_url(url, box * density)) for density in DENSITIES]
    if all(found for _, found in variants):
        attrs["src"] = variants[0][1]
        attrs["srcset"] = ", ".join(f"{found} {density}x" for density, found in variants)
    return attrs


def is_variant(path: str) -> bool:
    return f"/{frontend_setting('media_variants')['dir']}/" in f"/{path.lstrip('/')}"


def cache_control_for(path: str, default: str) -> str:
    """An immutable year for a variant (its name changes with its source), else ``default``."""
    if is_variant(path):
        return f"public, max-age={frontend_setting('media_variants')['max_age']}, immutable"
    return default
