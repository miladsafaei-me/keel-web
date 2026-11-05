"""Sidebar pieces for the panel's own pages, for the host's ``nav`` callable to place."""
from __future__ import annotations

from django.urls import reverse


def _item(label, icon, name):
    url = reverse(f"keel_web_panel:{name}")
    return {"label": label, "icon": icon, "url": url, "match_prefix": url}


def dashboard_item():
    return {**_item("Dashboard", "dashboard", "dashboard"), "exact": True}


def account_section(request):
    items = []
    if request.user.is_superuser:
        items.append(_item("Users", "users", "user_list"))
    items.append(_item("Your password", "lock", "password_change"))
    return {"label": "Accounts", "items": items}
