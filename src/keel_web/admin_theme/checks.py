"""System check: the theme only replaces Django's admin when it is listed first."""
from __future__ import annotations

from django.conf import settings
from django.core import checks

THEME_APP = "keel_web.admin_theme"
ADMIN_APP = "django.contrib.admin"


def _index(apps, name):
    for position, entry in enumerate(apps):
        if entry == name or entry.startswith(name + "."):
            return position
    return None


@checks.register(checks.Tags.templates)
def check_theme_precedes_admin(app_configs=None, **kwargs):
    apps = list(settings.INSTALLED_APPS)
    theme, admin = _index(apps, THEME_APP), _index(apps, ADMIN_APP)
    if theme is None or admin is None or theme < admin:
        return []
    return [
        checks.Error(
            f"{THEME_APP} must come before {ADMIN_APP} in INSTALLED_APPS.",
            hint="Its admin templates and icons replace Django's only when its app is found first.",
            id="keel_web_admin_theme.E001",
        )
    ]
