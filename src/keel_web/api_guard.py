"""Keep a site's own API endpoints to the site's own pages.

**The problem this exists for.** An endpoint a page fetches -- a JSON list behind a
comparison table, an HTML fragment behind a filter -- is a URL like any other. A crawler
can index it, a shared edge cache can store one caller's answer and hand it to the next,
and a script can pull the whole dataset behind it in one request without loading a page.
None of that is what the endpoint is for.

**What it does, for every request under a configured prefix (``/api/`` by default):**
  * Every response, answered or refused, carries ``X-Robots-Tag`` (``noindex`` by
    default) and ``Cache-Control: private, no-store``. Both are set last, over whatever
    the view or an inner middleware wrote -- ``AnonymousPageCacheMiddleware`` included --
    so no shared cache ever holds a guarded answer to replay without asking the origin.
  * The request is answered only when one of these holds, and refused with a 403 otherwise:
      1. It carries ``Authorization: Bearer <token>`` naming one of ``access_tokens``.
         This is the grant for a caller that is not one of the site's pages.
      2. The browser marks it ``Sec-Fetch-Site: same-origin``: a fetch, or a link
         followed, from a page on this same origin.
      3. Its ``Origin`` header, or failing that its ``Referer``, names this request's own
         host or one of ``trusted_origins``. This covers a browser that sends no fetch
         metadata, and a trusted site calling from its own pages.

**What it is not.** A browser sets fetch metadata, ``Origin`` and ``Referer`` itself and a
page's script cannot forge them, so rules 2 and 3 do keep other sites' pages out. A
program that is not a browser can send any header it likes, so neither rule is
authentication, and a scraper that copies the headers gets through. Only a token is a
grant; data that must stay private belongs behind real authentication, not behind this.

**Position.** Directly after ``SecurityMiddleware``, above every middleware that writes
``Cache-Control``, so its headers are the last word on the way out and a refused request
stops before sessions, authentication or the view run.

**Configuration** -- ``KEEL_WEB["api_guard"]``, off by default; see ``keel_web/config.py``.
"""

from __future__ import annotations

import hmac
from urllib.parse import urlsplit

from django.http import HttpRequest, HttpResponse, JsonResponse

from .config import api_guard_setting

REFUSAL = "This endpoint answers requests from this site's own pages only."


class ApiGuardMiddleware:
    """Answer a guarded path only for the site's own pages, a trusted origin or a token."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not api_guard_setting("enabled") or not self._guarded(request.path):
            return self.get_response(request)
        if self._allowed(request):
            response = self.get_response(request)
        else:
            response = JsonResponse({"detail": REFUSAL}, status=403)
        response["X-Robots-Tag"] = api_guard_setting("robots")
        response["Cache-Control"] = "private, no-store"
        return response

    @staticmethod
    def _guarded(path: str) -> bool:
        return any(path.startswith(prefix) for prefix in api_guard_setting("prefixes"))

    def _allowed(self, request: HttpRequest) -> bool:
        return (
            self._carries_token(request)
            or request.headers.get("Sec-Fetch-Site") == "same-origin"
            or self._from_trusted_page(request)
        )

    @staticmethod
    def _carries_token(request: HttpRequest) -> bool:
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        token = token.strip()
        if scheme.lower() != "bearer" or not token:
            return False
        return any(hmac.compare_digest(token, str(granted)) for granted in api_guard_setting("access_tokens") if granted)

    @staticmethod
    def _from_trusted_page(request: HttpRequest) -> bool:
        source = request.headers.get("Origin") or request.headers.get("Referer") or ""
        parts = urlsplit(source)
        if not parts.scheme or not parts.netloc:
            return False
        if parts.netloc.lower() == request.get_host().lower():
            return True
        trusted = {origin.rstrip("/").lower() for origin in api_guard_setting("trusted_origins")}
        return f"{parts.scheme}://{parts.netloc}".lower() in trusted
