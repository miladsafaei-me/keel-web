"""Account login signal handlers.

On every login (form or social), claim the new session as the account's single
active session and tear down the previously active one, so only one device/IP
can use an account at a time. The companion ``SingleSessionMiddleware`` signs
out any stragglers on their next request.
"""
from __future__ import annotations

from django.contrib.auth.signals import user_logged_in
from django.contrib.sessions.models import Session
from django.dispatch import receiver


@receiver(user_logged_in)
def enforce_single_session(sender, request, user, **kwargs):
    if request is None or not hasattr(request, "session"):
        return

    # Staff/superusers are exempt — they routinely run several concurrent
    # sessions (a staff panel + a client view, multiple tabs, automated checks),
    # so claiming one as the single active session and DELETING the others would
    # pull a live session row out from under another tab; that tab's next
    # session-saving request then raises Django's SessionInterrupted -> 400 Bad
    # Request. This mirrors the matching exemption in ``SingleSessionMiddleware``
    # (the two halves must agree, or one re-introduces the other's bug).
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return

    # Django cycles the session key during login(), so it is set by the time
    # this signal fires; ensure one exists before claiming it.
    session = request.session
    if session.session_key is None:
        session.save()
    new_key = session.session_key

    previous_key = getattr(user, "current_session_key", "") or ""
    if previous_key and previous_key != new_key:
        # Drop the displaced session immediately (best-effort; the middleware
        # is the durable guard if this row is already gone).
        Session.objects.filter(session_key=previous_key).delete()

    if previous_key != new_key:
        user.current_session_key = new_key
        user.save(update_fields=["current_session_key", "updated_at"])
