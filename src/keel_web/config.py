"""Host configuration surface for keel-web.

A consuming project configures keel-web through a ``KEEL_WEB`` settings dict.
Every key is optional; the defaults make the package usable standalone. Anything
that reached into SignalBots domain code in the original source is exposed here
as a hook (a dotted path to a host callable) so keel-web itself stays
domain-neutral.

    KEEL_WEB = {
        # Group whose members (plus superusers) may reach the content-CMS shell
        # and switch into the staff panel.
        "content_editor_group": "Content Editor",
        # Named URL a denied staff request is redirected to (authenticated but
        # not permitted). Falls back to LOGIN_URL for anonymous requests.
        "permission_denied_redirect": "home",
        # Restrict the account-status email-verify banner + resend flow to this
        # path prefix (so the EmailAddress lookup never runs on public pages).
        "client_path_prefix": "/client/",
        # DB table for the concrete User model. Point at an existing table (e.g.
        # "users_user") to adopt keel-web's User into a project that already has
        # one, with only a state-level AlterModelTable migration.
        "user_db_table": "keel_web_auth_user",
        # Optional dotted path to a host callable invoked after a gated signup
        # (a signup that carried a ``signup_src`` product key). Signature:
        # ``hook(*, user, product_key, request) -> None``. Best-effort; any
        # failure is swallowed so it can never break the signup itself.
        "signup_lead_hook": None,
        # Client-panel sidebar navigation. A dotted path to either a tuple of
        # NavSection (see client/navigation.py) or a zero-arg callable returning
        # one. Default: empty nav — the host supplies its own product nav.
        "client_nav": None,
        # Optional dotted path to ``fn(request) -> dict`` merged into the context
        # of every client-panel view — where the host injects panel-wide extras
        # (e.g. an activation banner, a support-bot URL) that keel-web must not
        # hardcode. Default: none.
        "client_base_context_hook": None,
        # Branding used by the transactional-email chrome. ``brand_name`` and the
        # logo path also read from top-level BRAND_NAME / SITE_BASE_URL settings.
        "email_logo_static": "img/email/logo.png",

        # Manifest-static storage tuning (see storage.py).
        "static_skip_hash_prefixes": ("client/tailwind/",),
        "static_minify_skip_substrings": (
            ".min.css", ".min.js", "/vendor/", "admin/",
        ),

        # AI image-generation resolvers. Each is a dotted path to a host callable
        # so the API key / endpoint / prompt come from the host's own settings or
        # a DB-backed AiSetting resolver rather than being hardcoded here.
        "image_gen": {
            "api_key_hook": None,        # () -> str        (default: settings.GEMINI_API_KEY)
            "hero_url_hook": None,       # () -> str        (default: built from model setting)
            "inline_url_hook": None,     # () -> str
            "aspect_ratio_hook": None,   # () -> "16:9"|"4:3"|"1:1"
            "hero_system_instruction_hook": None,   # () -> str
            "inline_system_instruction_hook": None, # () -> str
        },

        # Edge-cacheability for anonymous GET/HEAD of public pages. See
        # keel_web/cache.py for the full story. Off by default: no consumer's
        # behaviour changes just from upgrading the package.
        "anonymous_page_cache": {
            "enabled": False,
            # Path prefixes that legitimately need a real session or a
            # personalised response (own auth/admin/client areas by default;
            # add a host's own forum/account paths on top of these).
            "exempt_prefixes": ("/admin", "/accounts", "/client"),
            "browser_max_age": 300,   # Cache-Control max-age (seconds)
            "edge_max_age": 3600,     # Cache-Control s-maxage (seconds)
            # Cache-Control stale-while-revalidate (seconds), or None to omit it.
            # Lets an edge serve its copy while it refetches in the background.
            "stale_while_revalidate": None,
            # Vary header field names to strip, e.g. ("Accept-Language",) on a
            # site that serves exactly one language from every URL. Opt-in
            # only — never drop a field a site's URLs genuinely vary on.
            "vary_drop": (),
            # Drop a CSRF cookie from an otherwise-eligible response. Off by
            # default: a page with a real POST form needs that cookie. The
            # better fix for a page that only ever renders {% csrf_token %} in
            # a GET-only form (a header search box, say) is usually to stop
            # rendering the token there, not to strip the cookie here.
            "drop_csrf_cookie": False,
        },
    }
"""
from __future__ import annotations

from django.conf import settings
from django.utils.module_loading import import_string

_DEFAULTS = {
    "content_editor_group": "Content Editor",
    "permission_denied_redirect": "home",
    "client_path_prefix": "/client/",
    "user_db_table": "keel_web_auth_user",
    "signup_lead_hook": None,
    "email_logo_static": "img/email/logo.png",
    "static_skip_hash_prefixes": ("client/tailwind/",),
    "static_minify_skip_substrings": (
        ".min.css",
        ".min.js",
        "/vendor/",
        "client/css/",
        "client/tailwind/",
        "admin/",
        "unfold/",
    ),
    "image_gen": {
        "api_key_hook": None,
        "hero_url_hook": None,
        "inline_url_hook": None,
        "aspect_ratio_hook": None,
        "hero_system_instruction_hook": None,
        "inline_system_instruction_hook": None,
    },
    "anonymous_page_cache": {
        "enabled": False,
        "exempt_prefixes": ("/admin", "/accounts", "/client"),
        "browser_max_age": 300,
        "edge_max_age": 3600,
        "stale_while_revalidate": None,
        "vary_drop": (),
        "drop_csrf_cookie": False,
    },
}


def web_setting(key):
    """Return ``KEEL_WEB[key]`` or the package default for that key."""
    return getattr(settings, "KEEL_WEB", {}).get(key, _DEFAULTS[key])


def image_gen_setting(key):
    """Return ``KEEL_WEB["image_gen"][key]`` or its package default."""
    configured = getattr(settings, "KEEL_WEB", {}).get("image_gen", {}) or {}
    return configured.get(key, _DEFAULTS["image_gen"][key])


def anonymous_page_cache_setting(key):
    """Return ``KEEL_WEB["anonymous_page_cache"][key]`` or its package default."""
    configured = getattr(settings, "KEEL_WEB", {}).get("anonymous_page_cache", {}) or {}
    return configured.get(key, _DEFAULTS["anonymous_page_cache"][key])


def call_hook(dotted, *args, default=None, **kwargs):
    """Resolve a dotted-path hook and call it, returning ``default`` on any failure.

    Hooks are the config-contract seam: the host supplies domain behaviour (a
    lead recorder, an API-key resolver) without keel-web importing host code.
    """
    if not dotted:
        return default
    try:
        return import_string(dotted)(*args, **kwargs)
    except Exception:
        return default
