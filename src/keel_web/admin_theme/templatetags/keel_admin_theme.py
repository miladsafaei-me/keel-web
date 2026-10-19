"""Template tags of the admin theme: its settings, the sidebar and the model icons."""
from __future__ import annotations

from django import template
from django.urls import NoReverseMatch, reverse

from keel_web.auth.templatetags.keel_icons import icon as render_icon
from keel_web.config import admin_theme_setting

register = template.Library()

DEFAULT_MODEL_ICONS = {
    "auth.user": "users",
    "auth.group": "shield-check",
    "sites.site": "world-www",
    "redirects.redirect": "arrows-exchange",
    "flatpages.flatpage": "file-text",
}
DEFAULT_ICON = "file-text"


def _initials(text: str) -> str:
    words = [word for word in str(text).replace("·", " ").split() if word[:1].isalnum()]
    return "".join(word[0] for word in words[:2]).upper() or "A"


def _brand_name(context) -> str:
    configured = admin_theme_setting("brand_name")
    if configured:
        return configured
    return str(context.get("site_header") or "Administration")


def _resolve(url: str) -> str:
    if url.startswith(("/", "http://", "https://")):
        return url
    try:
        return reverse(url)
    except NoReverseMatch:
        return url


def model_icon_name(app_label: str, object_name: str) -> str:
    icons = {**DEFAULT_MODEL_ICONS, **admin_theme_setting("model_icons")}
    key = f"{app_label}.{object_name}".lower()
    return icons.get(key) or icons.get(app_label.lower()) or DEFAULT_ICON


@register.simple_tag(takes_context=True)
def admin_theme(context):
    """Everything the chrome needs from ``KEEL_WEB["admin_theme"]``, in one dict."""
    brand = _brand_name(context)
    default_theme = admin_theme_setting("default_theme")
    return {
        "brand_name": brand,
        "initials": _initials(brand),
        "tagline": admin_theme_setting("tagline"),
        "logo": admin_theme_setting("logo"),
        "logo_round": admin_theme_setting("logo_round"),
        "favicon": admin_theme_setting("favicon"),
        "stylesheets": tuple(admin_theme_setting("stylesheets")),
        "login_title": admin_theme_setting("login_title"),
        "login_text": admin_theme_setting("login_text"),
        "default_theme": default_theme if default_theme in ("auto", "light", "dark") else "auto",
    }


@register.simple_tag(takes_context=True)
def admin_nav(context):
    """The sidebar: Dashboard and the host's links, then one section per admin app.

    The item whose URL is the longest prefix of the current path is the active one,
    so a model stays lit on its add, change, history and delete pages.
    """
    request = context.get("request")
    path = request.path if request is not None else ""
    index_url = reverse("admin:index")

    menu = [{"label": "Dashboard", "url": index_url, "icon": "dashboard", "exact": True}]
    for link in admin_theme_setting("nav_links"):
        menu.append({"label": link["label"], "url": _resolve(link["url"]),
                     "icon": link.get("icon") or "link", "exact": False})
    sections = [{"label": "Menu", "items": menu}]

    for app in context.get("available_apps") or ():
        items = [
            {"label": model["name"], "url": model["admin_url"], "exact": False,
             "icon": model_icon_name(app["app_label"], model["object_name"])}
            for model in app["models"] if model.get("admin_url")
        ]
        if items:
            sections.append({"label": app["name"], "items": items})

    matching = [item["url"] for section in sections for item in section["items"]
                if (path == item["url"] if item["exact"] else path.startswith(item["url"]))]
    active = max(matching, key=len) if matching else None
    for section in sections:
        for item in section["items"]:
            item["active"] = item["url"] == active
    return sections


@register.simple_tag
def model_icon(app_label, object_name, css_class=""):
    """The icon of one model, as inline SVG."""
    return render_icon(model_icon_name(str(app_label), str(object_name)), **{"class": css_class})


@register.filter
def initials(user) -> str:
    """Up to two letters for the avatar of a user."""
    full = ""
    if hasattr(user, "get_full_name"):
        full = user.get_full_name() or ""
    if not full and hasattr(user, "get_username"):
        full = user.get_username()
    return _initials(full or "?")
