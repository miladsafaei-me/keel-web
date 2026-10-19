"""Re-export the ``keel_icons`` tag library, so the theme works without ``keel_web.auth``.

Same reason and same shared ``Library`` instance as ``admin_shell``'s re-export.
"""
from keel_web.auth.templatetags.keel_icons import register  # noqa: F401
