"""Anonymous public-page edge caching.

**The problem this exists for.** A Cloudflare Cache Rule that caches HTML at the
edge still refuses to cache any response carrying ``Set-Cookie`` or an
uncacheable ``Vary`` — correctly so, because Cloudflare cannot know whether that
cookie is a shared preference or one visitor's private session. Most Django
sites emit exactly that on every first-touch anonymous GET, because *something*
global in the middleware stack writes to the session (django-machina's
``ForumPermissionMiddleware`` doing it for every request, not just ``/forum/``,
is the confirmed case on one Keel consumer; another site's cause was
``LocaleMiddleware`` adding ``Vary: Accept-Language`` with no ``Cache-Control``
of its own to begin with). The result: a crawler — which never returns with a
cookie jar — pays full uncached origin cost on every fetch of every public URL,
and a new site's crawl rate is throttled by that response time. Find each
project's actual cause before assuming it matches another project's; a bare
``RequestFactory`` GET plus manual session/cookie inspection after each
middleware is how the reference case was confirmed, not guessed.

**Ordering (hard requirement).** This middleware must sit directly after
``django.contrib.sessions.middleware.SessionMiddleware`` in ``MIDDLEWARE``::

    MIDDLEWARE = [
        ...,
        "django.contrib.sessions.middleware.SessionMiddleware",
        "keel_web.cache.AnonymousPageCacheMiddleware",
        ...,
    ]

Django runs middleware top-down on the way in and bottom-up on the way out, so
at that position this middleware's post-response code runs *after* every inner
middleware (Common, Auth, Csrf, Locale, a host's own machina-style middleware —
whatever else writes to the session or the response) has had its turn, but
*before* ``SessionMiddleware.process_response`` — which is outside it in the
chain — decides whether to persist the session and emit ``Set-Cookie`` /
``Vary: Cookie``. Nothing has been saved to the session store yet at that point,
so resetting ``session.modified`` / ``session.accessed`` back to ``False`` makes
any inner write a pure in-memory no-op: ``SessionMiddleware`` sees an unmodified,
unaccessed session and skips the save, the ``Set-Cookie``, and the
``Vary: Cookie`` it would otherwise add.

**Eligibility (every one of these must hold):**
  * ``GET``/``HEAD`` — never touch a state-changing request.
  * path does not start with a configured ``exempt_prefixes`` entry — a host's
    auth/admin/forum/account areas legitimately need a real session or a
    personalised response.
  * the request arrived with **no** session cookie — a returning or logged-in
    visitor (anyone who already holds the session cookie) keeps Django's normal
    session handling completely untouched; only genuinely first-touch anonymous
    requests are eligible.
  * ``request.user`` is not authenticated (checked again defensively after the
    response comes back, in case auth middleware ran and logged someone in
    mid-request).
  * the response is a plain ``200`` — never cache a redirect, an error page, or
    a partial response at the edge.
  * the view has not already set its own ``Cache-Control`` — an explicit
    ``no-store``/``private`` from a view is a deliberate decision and wins.
  * after the session no-op and the optional CSRF-cookie drop below, the
    response still carries **no** ``Set-Cookie`` at all. Serving one visitor's
    cookie to another is the worst failure available here, so this check is
    never skipped: when in doubt, the response is left uncached.

**What an eligible response gets:**
  1. The session-save no-op described above.
  2. Configured ``vary_drop`` fields removed from ``Vary`` (case-insensitive).
     Never hardcoded: dropping ``Accept-Language`` buys a single-language site
     a cacheable page, but would silently serve the wrong language on a site
     that genuinely varies content on it — so a field is only ever removed when
     a host opts it in.
  3. Optionally, a CSRF cookie removed from the response (``drop_csrf_cookie``,
     default ``False``). Some pages set a CSRF cookie purely because a template
     renders ``{% csrf_token %}`` for a form that should have been a plain GET
     form (a header search box is the common case) and needs no token at all.
     Dropping the cookie on a page with a real POST form would break that form,
     so the honest default is off; the better fix is usually to stop rendering
     the token on pages that never post, not to strip the cookie here.
  4. ``Cache-Control: public, max-age=<browser_max_age>, s-maxage=<edge_max_age>``.

**Configuration** — ``KEEL_WEB["anonymous_page_cache"]``, all keys optional (see
``keel_web/config.py`` for the full table and defaults). Off by default
(``enabled: False``): installing or upgrading the package never changes a
consumer's cache behaviour on its own — it is opted into per host.
"""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from .config import anonymous_page_cache_setting


class AnonymousPageCacheMiddleware:
    """Make first-touch anonymous GET/HEAD of public pages edge-cacheable.

    See the module docstring for the full story, the required position in
    ``MIDDLEWARE`` (directly after ``SessionMiddleware``), and every
    eligibility rule.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not anonymous_page_cache_setting("enabled"):
            return self.get_response(request)
        eligible = self._is_eligible_request(request)
        response = self.get_response(request)
        if eligible:
            self._make_cacheable(request, response)
        return response

    def _is_eligible_request(self, request: HttpRequest) -> bool:
        if request.method not in ("GET", "HEAD"):
            return False
        path = request.path
        for prefix in anonymous_page_cache_setting("exempt_prefixes"):
            if path == prefix or path.startswith(prefix + "/"):
                return False
        session_cookie_name = settings.SESSION_COOKIE_NAME
        if session_cookie_name in request.COOKIES:
            # Returning visitor already holds a session cookie — leave
            # Django's normal session save/renew behaviour untouched for them.
            return False
        return True

    def _make_cacheable(self, request: HttpRequest, response: HttpResponse) -> None:
        if response.status_code != 200:
            return
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            return
        if "Cache-Control" in response:
            # The view made its own deliberate call (commonly an explicit
            # no-store/private) — never override it.
            return

        session = getattr(request, "session", None)
        if session is not None:
            # Nothing has been persisted yet — SessionMiddleware.process_response
            # (which does the actual save() + set_cookie()) runs after this,
            # since it is outside this middleware in the chain. Clearing these
            # two flags makes any in-memory write from an inner middleware a
            # pure no-op: no session-store write, no Set-Cookie, no
            # "Vary: Cookie".
            session.modified = False
            session.accessed = False

        vary_drop = {field.lower() for field in anonymous_page_cache_setting("vary_drop")}
        if vary_drop and "Vary" in response:
            remaining = [
                v.strip()
                for v in response["Vary"].split(",")
                if v.strip().lower() not in vary_drop
            ]
            if remaining:
                response["Vary"] = ", ".join(remaining)
            else:
                del response["Vary"]

        if anonymous_page_cache_setting("drop_csrf_cookie"):
            csrf_cookie_name = settings.CSRF_COOKIE_NAME
            if csrf_cookie_name in response.cookies:
                del response.cookies[csrf_cookie_name]

        if response.cookies:
            # Something on this response still legitimately sets a cookie.
            # Never mark a response carrying Set-Cookie as publicly cacheable
            # — serving one visitor's cookie to another is the failure every
            # rule above exists to prevent.
            return

        browser_max_age = anonymous_page_cache_setting("browser_max_age")
        edge_max_age = anonymous_page_cache_setting("edge_max_age")
        response["Cache-Control"] = f"public, max-age={browser_max_age}, s-maxage={edge_max_age}"
