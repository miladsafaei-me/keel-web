"""Re-export the ``keel_icons`` tag library from ``admin_shell``.

The admin shell base template (``base_admin.html``) and its navbar/sidebar load
``keel_icons``, whose canonical definition lives in ``keel_web.auth``. On the
subclass adoption path a host installs ``keel_web.admin_shell`` (and the client
CSS) but NOT ``keel_web.auth``, which would otherwise leave ``keel_icons``
unregistered and every shell page raising ``TemplateSyntaxError``. Re-exporting the
same ``Library`` instance here registers the tag whenever the admin shell is
installed, independent of the auth app. Django keys template-tag libraries by module
name, so when both apps are installed this simply resolves to the same shared
registry (no duplicate-registration error).
"""
from keel_web.auth.templatetags.keel_icons import register  # noqa: F401
