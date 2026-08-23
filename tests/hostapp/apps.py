from django.apps import AppConfig


class HostAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tests.hostapp"
    label = "keel_web_test_hostapp"
