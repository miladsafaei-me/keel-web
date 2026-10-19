from django.apps import AppConfig


class KeelWebAdminThemeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "keel_web.admin_theme"
    label = "keel_web_admin_theme"
    verbose_name = "Keel Web: Admin theme"

    def ready(self):
        from . import checks  # noqa: F401
