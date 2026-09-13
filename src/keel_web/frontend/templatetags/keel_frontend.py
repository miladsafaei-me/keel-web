"""Template tags for keel_web.frontend.

    {% load keel_frontend %}
    {% css_bundle "site" %}                      one <link>, or one per source when unbuilt
    {% icon_font_preload %}                      preload for the solid icon font in use
    {% media_img url 48 48 class="logo" alt="" %}  <img> with WebP src + 1x/2x srcset
"""

from __future__ import annotations

import posixpath

from django import template
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ...config import frontend_setting
from .. import bundles, icons, images

register = template.Library()


def _link(href: str) -> str:
    return format_html('<link rel="stylesheet" href="{}">', href)


def _icon_subset_path(filename: str) -> str:
    return f"{frontend_setting('bundle_dir')}/{icons.SUBSET_DIR}/{filename}"


def _subset_ready(path: str) -> bool:
    return bool(frontend_setting("enabled")) and bundles.find_source(path) is not None


@register.simple_tag
def css_bundle(name):
    """The stylesheet link(s) for bundle ``name``; see ``keel_web.frontend.bundles``."""
    try:
        paths = bundles.sources(name)
    except KeyError as exc:
        raise template.TemplateSyntaxError(str(exc)) from exc
    if bundles.use_bundle(name):
        return _link(static(bundles.static_path(name)))
    links = []
    for path in paths:
        if path == _icon_subset_path(icons.SUBSET_CSS) and not _subset_ready(path):
            path = frontend_setting("icons").get("css")
            if not path:
                continue
        links.append(_link(static(path)))
    return mark_safe("\n".join(links))


@register.simple_tag
def icon_font_preload(stem="fa-solid-900"):
    """Preload the icon font the first screen draws with: the subset when built, else stock."""
    subset = _icon_subset_path(f"{stem}.subset.woff2")
    if _subset_ready(subset):
        href = static(subset)
    else:
        stock = frontend_setting("icons").get("css")
        if not stock:
            return ""
        href = static(posixpath.normpath(posixpath.join(posixpath.dirname(stock), "../webfonts", f"{stem}.woff2")))
    return format_html('<link rel="preload" href="{}" as="font" type="font/woff2" crossorigin>', href)


@register.simple_tag
def media_img(src, width, height, **attrs):
    """An ``<img>`` drawn in a ``width`` x ``height`` box, with WebP variants for media files.

    Every other keyword becomes an attribute: ``True`` writes a bare attribute, ``False``
    and ``None`` write nothing, and ``data_*``/``aria_*`` names are written with hyphens.
    """
    ordered = {"class": attrs.pop("class", None)}
    ordered.update(images.img_attrs(src or "", width, height))
    for key, value in attrs.items():
        name = key.replace("_", "-") if key.startswith(("data_", "aria_")) else key
        ordered[name] = value
    parts = []
    for key, value in ordered.items():
        if value is None or value is False:
            continue
        parts.append(format_html(" {}", key) if value is True else format_html(' {}="{}"', key, value))
    return format_html("<img{}>", mark_safe("".join(parts)))
