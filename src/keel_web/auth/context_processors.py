"""Template context processors for the auth foundation."""
from __future__ import annotations

from ..config import web_setting


def account_status(request):
    """Expose ``account_email_unverified`` to client-panel templates.

    Drives the "verify your email" banner. Scoped to the client-panel path
    prefix (``KEEL_WEB["client_path_prefix"]``) so the EmailAddress lookup never
    runs on public marketing pages.
    """
    if not request.path.startswith(web_setting("client_path_prefix")):
        return {}

    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    if not user.email:
        return {"account_email_unverified": False}

    from allauth.account.models import EmailAddress

    verified = EmailAddress.objects.filter(user=user, verified=True).exists()
    return {"account_email_unverified": not verified}
