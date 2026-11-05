"""Shell settings for the staff-panel templates: ``{% panel_url "logout_url" as url %}``,
``{% panel_stylesheets %}`` and ``{% panel_setting "logo" as logo %}``."""
from __future__ import annotations

from django import template
from django.templatetags.static import static
from django.utils.html import format_html, format_html_join

from ...config import admin_shell_setting
from ..context import panel_url as _panel_url

register = template.Library()


@register.simple_tag
def panel_url(key):
    return _panel_url(key)


@register.simple_tag
def panel_setting(key):
    return admin_shell_setting(key)


@register.simple_tag
def panel_stylesheets():
    """The shell's stylesheet (the built Tailwind bundle), then the host's own."""
    paths = [admin_shell_setting("stylesheet"), *admin_shell_setting("stylesheets")]
    return format_html_join("\n", '<link rel="stylesheet" href="{}">', ((static(p),) for p in paths if p))


@register.simple_tag
def panel_favicon():
    path = admin_shell_setting("favicon")
    return format_html('<link rel="icon" href="{}">', static(path)) if path else ""
