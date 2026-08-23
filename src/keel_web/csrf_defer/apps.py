from django.apps import AppConfig


class CsrfDeferConfig(AppConfig):
    """Registers the ``keel_web_csrf`` static namespace (``deferred-csrf.js``).

    Installing this app is what makes Django's ``AppDirectoriesFinder`` pick up
    ``static/keel_web_csrf/js/deferred-csrf.js`` — it carries no models, no
    migrations, and needs no other app installed alongside it.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "keel_web.csrf_defer"
    label = "keel_web_csrf"
