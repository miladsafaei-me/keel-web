"""Account session-security middleware.

Enforces a single active session per account: when a user logs in from a new
device or IP, ``keel_web.auth.signals`` records that session's key on
``User.current_session_key`` (and drops the previous session). This middleware
is the enforcement half — any authenticated request whose session key no longer
matches the recorded one is logged out, so the displaced device is signed out on
its next request even if its session row still exists.
"""
from __future__ import annotations

from django.contrib.auth import logout


class SingleSessionMiddleware:
    """Log out requests whose session is no longer the account's active one.

    Staff/superusers are exempt: admins routinely operate several sessions
    (a staff panel + a client view, multiple tabs) and locking them to one is
    more disruptive than the single-session guarantee is worth for those
    accounts.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_staff:
            active_key = user.current_session_key
            current_key = request.session.session_key
            # Only act once an active session has been recorded for the user and
            # the current request carries a (different) established key.
            if active_key and current_key and current_key != active_key:
                logout(request)
        return self.get_response(request)
