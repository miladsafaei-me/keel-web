from django.apps import AppConfig


class KeelWebAdminConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "keel_web.admin_shell"
    label = "keel_web_admin"
    verbose_name = "Keel Web: Admin shell"
