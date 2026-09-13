"""Custom static-files storage backend.

Wraps Whitenoise's CompressedManifestStaticFilesStorage so every collected asset
gets a content-hashed URL (e.g. ``bundle.4e3b1f2c.css``) for free cache-busting,
and minifies CSS/JS in-place before the hash + gzip/brotli step so the shipped
bytes are also the smallest the source can produce.

Project-specific tuning (which prefixes to skip hashing, which paths to skip
minifying) is read from ``KEEL_WEB`` rather than hardcoded:

- ``static_skip_hash_prefixes`` — e.g. a Tailwind v4 source file containing
  ``@import "tailwindcss"`` (a source token, not a real URL) that the manifest
  post-processor cannot resolve. It is still copied + compressed, just un-hashed;
  nothing references it via ``{% static %}`` so the missing hash is invisible.
- ``static_minify_skip_substrings`` — already-minified vendor bundles / output
  the minifier should not touch.
"""
from __future__ import annotations

from whitenoise.storage import CompressedManifestStaticFilesStorage

from .config import web_setting

try:
    import rcssmin  # type: ignore
except ImportError:
    rcssmin = None

try:
    import rjsmin  # type: ignore
except ImportError:
    rjsmin = None


def _skip_hash_prefixes():
    return tuple(web_setting("static_skip_hash_prefixes"))


def _minify_skip_substrings():
    return tuple(web_setting("static_minify_skip_substrings"))


def _should_minify(name: str) -> bool:
    lower = name.lower()
    if any(skip in lower for skip in _minify_skip_substrings()):
        return False
    return lower.endswith(".css") or lower.endswith(".js")


def _maybe_minify(name: str, content_bytes: bytes) -> bytes:
    """Return minified bytes for CSS/JS we own; otherwise return as-is.

    Idempotent — running on already-minified content is a no-op. Any failure
    inside the minifier returns the original bytes so a bad rule never breaks
    collectstatic.
    """
    if not _should_minify(name):
        return content_bytes
    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return content_bytes
    try:
        if name.lower().endswith(".css") and rcssmin is not None:
            out = rcssmin.cssmin(text)
        elif name.lower().endswith(".js") and rjsmin is not None:
            out = rjsmin.jsmin(text)
        else:
            return content_bytes
    except Exception:
        return content_bytes
    if not out:
        return content_bytes
    out_bytes = out.encode("utf-8")
    return out_bytes if len(out_bytes) < len(content_bytes) else content_bytes


class KeelManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    # When a {% static %} reference points to a file we didn't post-process
    # (e.g. .webp siblings generated after collectstatic), fall back to the
    # un-hashed URL instead of raising ValueError. Those files still cache-bust
    # via Last-Modified / ETag.
    manifest_strict = False

    def stored_name(self, name):
        """The hashed name, or the plain one for a file that was never collected.

        ``manifest_strict = False`` alone does not deliver that: for a name missing
        from the manifest Django computes a hash from the file itself, and raises
        ``ValueError`` when the file is not on disk either. So one template line
        pointing at a stylesheet a package stopped shipping turned the whole page
        into a 500. The plain URL 404s for that one asset, which is what plain
        static storage did, and the page renders.
        """
        try:
            return super().stored_name(name)
        except ValueError:
            return name

    def _save(self, name, content):
        """Minify CSS/JS at write time so the bytes Django then content-hashes
        are already the smallest form. ManifestStaticFilesStorage derives both
        the hash and the on-disk copy from a single read; waiting until
        post_process would leave the hashed copy already written.
        """
        if rcssmin is None and rjsmin is None:
            return super()._save(name, content)
        if not _should_minify(name):
            return super()._save(name, content)
        try:
            content.seek(0)
            data = content.read()
            if isinstance(data, str):
                data = data.encode("utf-8")
            minified = _maybe_minify(name, data)
            if minified is not data:
                from django.core.files.base import ContentFile

                content = ContentFile(minified)
            else:
                content.seek(0)
        except Exception:
            try:
                content.seek(0)
            except Exception:
                pass
        return super()._save(name, content)

    def post_process(self, paths, dry_run=False, **options):
        skip = _skip_hash_prefixes()
        filtered = {
            name: storage_file
            for name, storage_file in paths.items()
            if not name.startswith(skip)
        }
        return super().post_process(filtered, dry_run, **options)
