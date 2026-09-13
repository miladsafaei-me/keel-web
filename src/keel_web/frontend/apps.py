from django.apps import AppConfig


class FrontendConfig(AppConfig):
    """Registers the ``keel_frontend`` template tags and ``build_frontend_assets``.

    No models and no migrations; installing it changes nothing until a template loads
    the tags or a build runs the command.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "keel_web.frontend"
    label = "keel_web_frontend"
