"""The stock Django admin, drawn in the Keel staff-panel look.

Install ``keel_web.admin_theme`` *before* ``django.contrib.admin`` in
``INSTALLED_APPS``: its ``admin/`` and ``registration/`` templates and its
``admin/img/`` icons then replace Django's own, so every admin page (login,
dashboard, lists, forms, inlines, confirmations, history, password pages) renders
in the theme with no Django stylesheet loaded. Configure it with
``KEEL_WEB["admin_theme"]`` (see ``keel_web/config.py``).
"""
