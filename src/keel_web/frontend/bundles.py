"""CSS bundles: one stylesheet request where a page used to link one per file.

Every ``<link rel="stylesheet">`` in ``<head>`` holds the first paint until it lands, and
on a phone connection each one costs a round trip whatever its size. A site that keeps
its CSS authored per concern (tokens, reset, shell, chrome, components, a page sheet)
therefore pays for its own tidiness on every visit. Lighthouse reports it as
"Render-blocking requests".

A host declares its bundles once, in ``KEEL_WEB["frontend"]["css_bundles"]``, as a name
mapped to an ordered list of static paths. ``manage.py build_frontend_assets``
concatenates each into ``<output_dir>/<bundle_dir>/<name>.css`` before ``collectstatic``
hashes it, and ``{% css_bundle "<name>" %}`` links it. The sources stay separate on disk.

**When a bundle is used.** Only with ``KEEL_WEB["frontend"]["enabled"]`` on and the
bundle file present. Otherwise the tag links each source on its own, exactly as the
page did before, so a local run, the test runner and a build that skipped the step all
still render a styled page. Hosts normally turn it on only in an image that ran the
build.

**Relative ``url()`` targets** are rewritten from each source's directory to the
bundle's, so fonts and images keep resolving and the manifest storage still hashes
them. Absolute paths, full URLs and ``data:`` URIs are left as written.
"""

from __future__ import annotations

import posixpath
import re
from pathlib import Path

from django.contrib.staticfiles import finders
from django.core.exceptions import ImproperlyConfigured

from ..config import frontend_setting

_URL_RE = re.compile(r"""url\(\s*(?P<quote>['"]?)(?P<target>[^'")]+)(?P=quote)\s*\)""")
_ABSOLUTE = ("data:", "http://", "https://", "//", "/", "#")


def declared() -> dict[str, tuple[str, ...]]:
    return {name: tuple(paths) for name, paths in (frontend_setting("css_bundles") or {}).items()}


def sources(name: str) -> tuple[str, ...]:
    bundles = declared()
    if name not in bundles:
        raise KeyError(f"unknown CSS bundle {name!r}: declare it in KEEL_WEB['frontend']['css_bundles']")
    return bundles[name]


def static_path(name: str) -> str:
    return f"{frontend_setting('bundle_dir')}/{name}.css"


def output_root() -> Path | None:
    configured = frontend_setting("output_dir")
    return Path(configured) if configured else None


def is_generated(path: str) -> bool:
    """A static path this package writes itself (a bundle, or the icon subset)."""
    return path.startswith(f"{frontend_setting('bundle_dir')}/")


def is_built(name: str) -> bool:
    root = output_root()
    return bool(root and (root / static_path(name)).is_file())


def use_bundle(name: str) -> bool:
    return bool(frontend_setting("enabled")) and is_built(name)


def find_source(path: str) -> Path | None:
    root = output_root()
    if root and is_generated(path) and (root / path).is_file():
        return root / path
    found = finders.find(path)
    return Path(found) if found else None


def missing_sources() -> list[str]:
    """``bundle: path`` for every declared source that does not resolve.

    Generated paths are skipped: they only exist once the build has run.
    """
    return [
        f"{name}: {path}"
        for name, paths in declared().items()
        for path in paths
        if not is_generated(path) and find_source(path) is None
    ]


def rebase_urls(css: str, source_path: str, bundle_path: str) -> str:
    source_dir = posixpath.dirname(source_path)
    bundle_dir = posixpath.dirname(bundle_path)

    def replace(match: re.Match[str]) -> str:
        target = match.group("target").strip()
        if target.startswith(_ABSOLUTE):
            return match.group(0)
        resolved = posixpath.normpath(posixpath.join(source_dir, target))
        return f"url('{posixpath.relpath(resolved, bundle_dir)}')"

    return _URL_RE.sub(replace, css)


def render(name: str) -> str:
    parts, missing = [], []
    for path in sources(name):
        found = find_source(path)
        if found is None:
            missing.append(path)
            continue
        css = found.read_text(encoding="utf-8")
        parts.append(f"/* {path} */\n{rebase_urls(css, path, static_path(name))}")
    if missing:
        raise FileNotFoundError(f"CSS bundle {name!r}: sources not found: {', '.join(missing)}")
    return "\n".join(parts) + "\n"


def build_all() -> list[tuple[str, int]]:
    """Write every declared bundle; remove bundle files no longer declared."""
    root = output_root()
    if root is None:
        raise ImproperlyConfigured("KEEL_WEB['frontend']['output_dir'] must name a static directory to build into.")
    out = root / frontend_setting("bundle_dir")
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name in declared():
        css = render(name)
        (out / f"{name}.css").write_text(css, encoding="utf-8")
        written.append((name, len(css.encode("utf-8"))))
    for stale in out.glob("*.css"):
        if stale.stem not in declared():
            stale.unlink()
    return written
