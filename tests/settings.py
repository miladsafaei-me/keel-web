"""Minimal Django settings to exercise keel_web.cache standalone.

Run with:

    DJANGO_SETTINGS_MODULE=tests.settings python -m django test tests

from the repo root, with keel-web installed (editable is fine) into whatever
interpreter runs the command.
"""
SECRET_KEY = "keel-web-test-suite"
DEBUG = True
ALLOWED_HOSTS = ["testserver"]
USE_TZ = True

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "keel_web.csrf_defer",
    "keel_web.frontend",
    "tests.hostapp",
]

STATIC_URL = "/static/"
MEDIA_URL = "/media/"

MIDDLEWARE = [
    "keel_web.api_guard.ApiGuardMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "keel_web.cache.AnonymousPageCacheMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "tests.hostapp.middleware.FakeTokenAuthMiddleware",
    "tests.hostapp.middleware.FakeStaffMiddleware",
    "keel_web.geo_block.GeoBlockMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    # Stands in for whatever host-specific middleware unconditionally writes to
    # the session on every request (django-machina's ForumPermissionMiddleware
    # in the reference case) -- placed after AnonymousPageCacheMiddleware in
    # this list, so it runs *inside* it, exactly like the real root cause does.
    "tests.hostapp.middleware.SessionWriterMiddleware",
]

ROOT_URLCONF = "tests.hostapp.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# Baseline test configuration: the capability is turned on so the behavioural
# tests exercise it. A dedicated test asserts the package-level default is
# False by overriding this away.
KEEL_WEB = {
    "anonymous_page_cache": {
        "enabled": True,
        "exempt_prefixes": ("/admin", "/accounts", "/client"),
        "browser_max_age": 300,
        "edge_max_age": 3600,
        "vary_drop": (),
        "drop_csrf_cookie": False,
    },
    "api_guard": {
        "enabled": True,
        "prefixes": ("/api/",),
        "trusted_origins": ("https://partner.example",),
        "access_tokens": ("granted-token",),
        "robots": "noindex",
    },
}
