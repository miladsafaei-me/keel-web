"""Test-only middleware standing in for two real-world causes.

``SessionWriterMiddleware`` stands in for a host-specific piece of global
middleware that unconditionally writes to the session on every request --
django-machina's ``ForumPermissionMiddleware`` in the reference case. It is
what ``AnonymousPageCacheMiddleware`` must neutralize.

``FakeTokenAuthMiddleware`` stands in for a non-session authentication scheme
(a bearer token, say) that can leave ``request.user`` authenticated even
though the request never carried a session cookie -- the case
``AnonymousPageCacheMiddleware``'s defensive ``request.user`` check guards
against.
"""

from __future__ import annotations

import uuid


class _FakeAuthenticatedUser:
    is_authenticated = True


class _FakeStaffUser:
    is_authenticated = True
    is_staff = True


class SessionWriterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.session["anonymous_key"] = uuid.uuid4().hex
        return self.get_response(request)


class FakeTokenAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.META.get("HTTP_X_FAKE_TOKEN_AUTH"):
            request.user = _FakeAuthenticatedUser()
        return self.get_response(request)


class FakeStaffMiddleware:
    """Signs the request in as staff when it carries ``X-Fake-Staff`` (geo_block tests)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.META.get("HTTP_X_FAKE_STAFF"):
            request.user = _FakeStaffUser()
        return self.get_response(request)
