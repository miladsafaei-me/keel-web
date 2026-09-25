"""Refuse visitors from countries a site has decided not to serve.

**The problem this exists for.** Some sites may not lawfully address readers in some
countries: a product banned for retail sale there, or a regulator that prosecutes the
people who promote it. Stating that in a footer does not keep anyone out, and people have
been convicted for the promotion, not for the link. A site that has made the decision
needs the page itself to refuse the visit.

**What it does.** A request whose country header (``CF-IPCountry`` by default, which a
Cloudflare-fronted origin receives on every request) names a configured country is
answered with ``451 Unavailable For Legal Reasons`` and ``Cache-Control: private,
no-store``. It is let through when:

  * it carries no country header at all -- a health check, a deploy smoke test, local
    development;
  * its path is under one of ``exempt_prefixes`` -- the site's own admin and login, so
    whoever runs the site from a blocked country can still sign in;
  * the user is signed in as staff (``exempt_staff``);
  * it comes from a **verified** search-engine crawler (``exempt_verified_crawlers``).
    The user agent alone proves nothing, since anyone can send ``Googlebot``: the client
    IP's reverse DNS name must end in that crawler's published domain and resolve
    forward to the same IP -- the check each search engine documents. Each IP's verdict
    is cached for a day.

**Shared caches are the leak, and this closes it by default.** An edge cache that does
not key on country serves its stored copy of a page to a blocked visitor without ever
asking the origin. So unless ``shared_cache`` is set, every response this middleware lets
through leaves as ``private``: a ``public`` or ``s-maxage`` directive is rewritten, and a
response with no ``Cache-Control`` is given ``private, max-age=<browser_max_age>``, which
also tells ``AnonymousPageCacheMiddleware`` that the call is already made. Set
``shared_cache`` only when the same countries are blocked at the edge as well (a
Cloudflare WAF rule, for instance), which runs before the edge cache.

**What it is not.** A VPN defeats a country check. The block shows that the site does not
serve those countries; the content has to show it too.

**Position.** After ``AuthenticationMiddleware`` (it reads ``request.user`` for the staff
exemption) and so inside ``AnonymousPageCacheMiddleware``, whose respect for an existing
``Cache-Control`` is what keeps a let-through page out of the edge cache.

**Configuration** -- ``KEEL_WEB["geo_block"]``, off by default; see ``keel_web/config.py``.
"""

from __future__ import annotations

import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string

from .config import geo_block_setting

DEFAULT_BODY = (
    "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
    "<meta name=\"robots\" content=\"noindex\"><title>Not available in your country</title>"
    "</head><body><main><h1>Not available in your country</h1>"
    "<p>This site does not serve readers in your country.</p></main></body></html>"
)

_CACHE_PREFIX = "keel_web:geo_block:crawler:"
_VERIFIED_TTL = 86400
_REFUSED_TTL = 3600
_DNS_TIMEOUT_SECONDS = 2.0
_dns_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="keel-geo-dns")


class GeoBlockMiddleware:
    """Answer 451 to a visitor from a configured country, and keep pages out of shared caches."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not geo_block_setting("enabled"):
            return self.get_response(request)
        if self._refused(request):
            return self._refusal(request)
        response = self.get_response(request)
        if not geo_block_setting("shared_cache"):
            _keep_out_of_shared_caches(response)
        return response

    def _refused(self, request: HttpRequest) -> bool:
        country = request.META.get(geo_block_setting("country_header"), "").strip().upper()
        if not country or country not in blocked_countries():
            return False
        if any(request.path.startswith(prefix) for prefix in geo_block_setting("exempt_prefixes")):
            return False
        if geo_block_setting("exempt_staff"):
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False) and getattr(user, "is_staff", False):
                return False
        if geo_block_setting("exempt_verified_crawlers") and is_verified_crawler(request):
            return False
        return True

    @staticmethod
    def _refusal(request: HttpRequest) -> HttpResponse:
        template = geo_block_setting("template")
        country = request.META.get(geo_block_setting("country_header"), "").strip().upper()
        body = render_to_string(template, {"country_code": country}, request=request) if template else DEFAULT_BODY
        response = HttpResponse(body, status=451)
        response["Cache-Control"] = "private, no-store"
        response["X-Robots-Tag"] = "noindex"
        return response


def blocked_countries() -> frozenset[str]:
    """The configured ISO 3166-1 alpha-2 codes, upper-cased."""
    return frozenset(str(code).strip().upper() for code in geo_block_setting("countries") if code)


def _keep_out_of_shared_caches(response: HttpResponse) -> None:
    current = response.get("Cache-Control", "")
    if not current:
        response["Cache-Control"] = f"private, max-age={geo_block_setting('browser_max_age')}"
        return
    directives = [d.strip() for d in current.split(",") if d.strip()]
    shared = ("public", "s-maxage", "stale-while-revalidate")
    kept = [d for d in directives if not d.lower().startswith(shared)]
    if len(kept) == len(directives):
        return
    if not any(d.lower() in ("private", "no-store") for d in kept):
        kept.insert(0, "private")
    response["Cache-Control"] = ", ".join(kept)


def is_verified_crawler(request: HttpRequest) -> bool:
    """True when the user agent names a configured crawler and its IP proves it by DNS."""
    agent = request.headers.get("User-Agent", "").lower()
    domains = None
    for token, suffixes in geo_block_setting("verified_crawlers"):
        if token.lower() in agent:
            domains = tuple(s.lower() for s in suffixes)
            break
    if not domains:
        return False
    ip = client_ip(request)
    if not ip:
        return False
    key = f"{_CACHE_PREFIX}{ip}:{'|'.join(domains)}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        verified = _dns_pool.submit(_dns_confirms, ip, domains).result(timeout=_DNS_TIMEOUT_SECONDS)
    except FutureTimeout:
        verified = False
    cache.set(key, verified, _VERIFIED_TTL if verified else _REFUSED_TTL)
    return verified


def client_ip(request: HttpRequest) -> str:
    """The visitor's IP from the configured header, else ``REMOTE_ADDR``; '' if unusable."""
    raw = request.META.get(geo_block_setting("client_ip_header"), "") or request.META.get("REMOTE_ADDR", "")
    raw = raw.split(",")[0].strip()
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return ""


def _dns_confirms(ip: str, domains: tuple[str, ...]) -> bool:
    try:
        host = socket.gethostbyaddr(ip)[0].lower().rstrip(".")
    except OSError:
        return False
    if not any(host == d.lstrip(".") or host.endswith("." + d.lstrip(".")) for d in domains):
        return False
    try:
        forward = {info[4][0].split("%")[0] for info in socket.getaddrinfo(host, None)}
    except OSError:
        return False
    normalized = set()
    for address in forward:
        try:
            normalized.add(str(ipaddress.ip_address(address)))
        except ValueError:
            continue
    return ip in normalized
