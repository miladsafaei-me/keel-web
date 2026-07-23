"""Template helpers for the client-panel sidebar and chrome."""
from __future__ import annotations

from django import template
from django.templatetags.static import static
from django.utils.safestring import mark_safe

from ...config import web_setting

register = template.Library()


@register.simple_tag
def persona_avatar(user, size_classes: str = "h-10 w-10", *, extra_classes: str = "") -> str:
    """Render a layered persona SVG, an uploaded image, or an initials fallback.

    Use as ``{% persona_avatar request.user "h-20 w-20" %}``. ``size_classes``
    sets the outer wrapper size; the SVG layers stretch to fill via absolute
    positioning. Falls back to the user's initials when no avatar is set.
    """
    if user is None or not user.is_authenticated:
        return mark_safe(
            f'<span class="inline-flex items-center justify-center {size_classes} '
            f'rounded-full bg-gray-200 text-gray-500 {extra_classes}">?</span>'
        )

    base = (
        f'<span class="relative inline-block overflow-hidden rounded-full '
        f'bg-gray-100 dark:bg-gray-800 {size_classes} {extra_classes}">'
    )

    # 1) Uploaded image wins.
    if getattr(user, "avatar", None):
        try:
            url = user.avatar.url
            return mark_safe(
                f'{base}<img src="{url}" alt="" class="absolute inset-0 h-full w-full object-cover"></span>'
            )
        except ValueError:
            pass

    # 2) Layered persona config.
    layers = getattr(user, "avatar_persona_layers", None) or []
    if layers:
        parts = [base]
        for folder, filename in layers:
            url = static(f"keel_web_client/img/personas/{folder}/{filename}")
            parts.append(
                f'<img src="{url}" alt="" class="absolute inset-0 h-full w-full" aria-hidden="true">'
            )
        parts.append("</span>")
        return mark_safe("".join(parts))

    # 3) Initials fallback.
    initials = getattr(user, "initials", "?")
    return mark_safe(
        f'<span class="inline-flex items-center justify-center {size_classes} '
        f'rounded-full bg-gray-100 text-gray-700 font-semibold dark:bg-gray-800 '
        f'dark:text-gray-300 {extra_classes}">{initials}</span>'
    )


@register.filter(name="can_switch_panels")
def can_switch_panels(user) -> bool:
    """True for superusers and members of the Content-Editor group."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=web_setting("content_editor_group")).exists()


@register.filter(name="is_active_path")
def is_active_path(prefix: str, current_path: str) -> bool:
    """Return True when current_path is at or below the navigation prefix.

    Dashboard prefix ``/client/`` would otherwise match every client page; for
    that exact case we require an equality match instead of a prefix match.
    """
    if not prefix or not current_path:
        return False
    if prefix == "/client/":
        return current_path == "/client/" or current_path == "/client"
    return current_path.startswith(prefix)


@register.filter(name="nav_item_active")
def nav_item_active(item, current_path: str) -> bool:
    """Active-state check that respects ``NavItem.exact``.

    With ``exact=True``, only the exact match (with or without a trailing slash)
    lights up — so a parent like a program overview does not stay active while
    the user is browsing a child route.
    """
    prefix = getattr(item, "match_prefix", "") or ""
    if not prefix or not current_path:
        return False
    if getattr(item, "exact", False) or prefix == "/client/":
        return current_path == prefix or current_path == prefix.rstrip("/")
    return current_path.startswith(prefix)
