"""URL fragment for ``keel_web.csrf_defer`` — the deferred-CSRF token endpoint.

Mount this once, unmodified, at the root of a consumer's URLconf::

    urlpatterns = [
        ...,
        path("", include("keel_web.csrf_defer.urls")),
        ...,
    ]

That puts the endpoint at ``/csrf-token/`` on every consumer. Mount it at that
same bare path everywhere rather than nesting it under a per-project prefix —
``keel_web_csrf/js/deferred-csrf.js`` hardcodes ``/csrf-token/`` as its
``ENDPOINT`` constant, and the two sides only agree on the URL because both
hardcode the same one. If a host's root URLconf genuinely cannot spare
``/csrf-token/`` (an existing route already there), do not remount this
fragment elsewhere — patch the JS constant in that one host instead and say so
loudly in that project's own docs, since it now differs from every other
consumer.
"""

from __future__ import annotations

from django.urls import path

from .views import csrf_token_view

app_name = "keel_web_csrf"

urlpatterns = [
    path("csrf-token/", csrf_token_view, name="csrf_token"),
]
