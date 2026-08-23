"""Deferred CSRF: fetch a token on demand instead of shipping one with the page.

**The problem this exists for.** A page that renders ``{% csrf_token %}`` makes
Django set a ``csrftoken`` cookie on the response, and Cloudflare (or any shared
edge cache) refuses to cache any response carrying ``Set-Cookie`` — correctly
so, since it cannot tell a shared preference from one visitor's private data.
So a single form that is merely *incidental* to a page (a newsletter box, a
header search field) is enough to make every response that includes it
uncacheable at the edge, even though nothing about the page itself is
personalised. ``keel_web.cache.AnonymousPageCacheMiddleware`` fixes the session
cookie half of this; it cannot fix the CSRF cookie half, because dropping that
cookie from a page whose form genuinely posts would just break the form. This
module is the real fix for that other half.

**How it works.** The page ships with no CSRF token and no CSRF cookie at all,
so it is eligible for edge caching. ``keel_web_csrf/js/deferred-csrf.js``
fetches a token from ``csrf_token_view`` below — on first focus of the form,
ideally, so the round trip is hidden behind the visitor's own typing — and
injects it into the form's hidden input before the form actually submits.

**The trade-off, stated plainly — read this before wiring it up anywhere.**
Deferred CSRF trades one page-load cookie for one extra request at submit
time, plus a new failure mode (the token fetch itself can fail). That trade is
only worth making for a form that is **incidental** to the page's purpose — a
newsletter signup, a header search box — where the page is worth caching with
or without that particular form working. A page whose *purpose* **is** the
form — login, signup, checkout, anything the visitor came to that page to do —
should keep the ordinary ``{% csrf_token %}`` and simply not be marked
cacheable. Deferring CSRF there only adds latency and a failure mode to the one
thing the page exists to do; it buys nothing, because that page was never
going to be cacheable anyway (it is personalised or state-changing by nature).

**Security does not regress.** This changes nothing about CSRF protection
itself. The token still comes from Django's own CSRF machinery (``get_token``),
the cookie is still set the ordinary way (``ensure_csrf_cookie``), and every
POST anywhere on the site — including one carrying a token fetched here — is
still checked by ``CsrfViewMiddleware`` exactly as before. Nothing here is
``@csrf_exempt``; this view only moves *when* a token is issued, never whether
one is required.

**Why this view itself can never be cached.** It always sets its own
``Cache-Control: no-store``, so no edge or browser cache rule can serve a
stale token or, worse, one visitor's token to another. It also always sets a
``Set-Cookie`` (via ``ensure_csrf_cookie``), which alone would already stop
``AnonymousPageCacheMiddleware`` — or any Cloudflare Cache Rule keyed on
``Set-Cookie`` — from treating it as cacheable, even without the explicit
header. It carries ``X-Robots-Tag: noindex`` since it is a JSON endpoint, not
a page, and it is kept deliberately tiny: one field, no HTML.
"""

from __future__ import annotations

from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET


@require_GET
@ensure_csrf_cookie
@cache_control(no_store=True)
def csrf_token_view(request):
    """Return ``{"csrfToken": "..."}`` and set the CSRF cookie on the response.

    ``ensure_csrf_cookie`` guarantees the cookie is set even though this view
    renders no template and calls no ``{% csrf_token %}`` — that is exactly
    what lets a *page* skip the cookie entirely and get both the cookie and
    the token from here instead, on demand.
    """
    response = JsonResponse({"csrfToken": get_token(request)})
    response["X-Robots-Tag"] = "noindex"
    return response
