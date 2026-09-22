from django.apps import AppConfig


class KeelWebAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "keel_web.auth"
    # Explicit label: the default (last path segment "auth") collides with
    # django.contrib.auth. This is the collision-safe namespacing contract.
    label = "keel_web_auth"
    verbose_name = "Keel Web: Auth foundation"

    def ready(self):
        from . import signals  # noqa: F401  (wire the single-session login receiver)
