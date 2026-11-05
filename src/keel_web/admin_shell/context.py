"""What every staff-panel page needs: the host's sidebar, the brand, and the access rule.

The host names its sidebar in ``KEEL_WEB["admin_shell"]["nav"]``: a dotted path to
``fn(request) -> sections`` (the structure ``resolve_nav_active`` takes). Packages that
ship panel pages (keel-booking, the newsletter, the users screens) render through
``PanelMixin`` or ``render_panel``, so every page carries the same sidebar whichever
package drew it.
"""
from __future__ import annotations

from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.utils.module_loading import import_string

from ..config import admin_shell_setting
from .nav import resolve_nav_active
from .permissions import AdminShellMixin


def panel_url(key: str) -> str:
    """The URL the shell setting ``key`` names: a path as given, a URL name reversed, else ""."""
    value = admin_shell_setting(key)
    if not value:
        return ""
    if value.startswith("/") or "://" in value:
        return value
    try:
        return reverse(value)
    except NoReverseMatch:
        return ""


def panel_nav(request) -> list:
    """The host's sidebar for ``request``, with the active item marked."""
    dotted = admin_shell_setting("nav")
    if not dotted:
        return []
    return resolve_nav_active(import_string(dotted)(request), request.path)


def panel_context(request, **extra) -> dict:
    return {"admin_nav": panel_nav(request), "brand_name": admin_shell_setting("brand_name"), **extra}


def render_panel(request, template: str, context: dict | None = None, **kwargs):
    """Render ``template`` inside the shell, with the sidebar and brand added."""
    return render(request, template, panel_context(request, **(context or {})), **kwargs)


def staff_required(view):
    """A function view open to signed-in staff only; anyone else goes to the sign-in page."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_staff):
            return redirect_to_login(request.get_full_path(), login_url=settings.LOGIN_URL)
        return view(request, *args, **kwargs)

    return wrapped


class PanelMixin(AdminShellMixin):
    """A class-based panel page: staff only, inside the shell, with a title over the content."""

    page_title = ""
    page_pretitle = ""
    page_subtitle = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        for key, value in panel_context(self.request).items():
            ctx.setdefault(key, value)
        for key in ("page_title", "page_pretitle", "page_subtitle"):
            if getattr(self, key):
                ctx.setdefault(key, getattr(self, key))
        return ctx
