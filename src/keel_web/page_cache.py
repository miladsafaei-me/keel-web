"""Serve an expensive page from the cache until the data behind it changes.

**The problem this exists for.** A data-heavy public page — a ranked board, a
comparison desk, a homepage that reads a whole roster — can take seconds of
Python to build while its data changes a few times a week. Django's own
``cache_page`` answers with a fixed timeout, which is either too short to help
or long enough to publish yesterday's figures. What such a page needs is a
cache that holds for as long as its data holds and not a request longer.

**How "the data changed" is known.** :func:`data_fingerprint` digests every row
version of the models a page reads. On PostgreSQL each row carries ``xmin`` (the
transaction that wrote it) and ``ctid`` (where that version sits), and any
``INSERT``, ``UPDATE`` or ``DELETE`` changes one of them or the row count — so
the digest moves on every write path there is: ``save()``,
``save(update_fields=[...])`` that leaves ``updated_at`` alone,
``QuerySet.update()``, ``bulk_update()``, raw SQL, a migration. A timestamp
column misses all but the first. Reading the two system columns never touches
TOAST, so the query costs well under a millisecond on tables of a few thousand
rows. Other databases fall back to row count and highest primary key, which
detects inserts and deletes but not updates; there, pass a short ``timeout``.

**What is stored, and for whom.** :func:`cached_page` keeps one entry per
*slot* — a string the host builds from whatever makes two renders differ: the
view, the viewer class (public or staff), the scheme and the host. Beside the
body it stores the *version* it was rendered at: the fingerprint plus anything
else that invalidates (the deployed release, the date, when a page prints the
year). Nothing about the viewer is read here, so choosing the slot is the host's
whole responsibility: **never share a slot between viewers who would see
different HTML.** A request with a query string is a slot of its own at best
and an unbounded number of them at worst; hosts should render those directly.

**Order of events on a request.**
  * Entry at the current version: served (``X-Keel-Page-Cache: hit``).
  * Stale or missing entry: this worker takes a short lock, renders, stores the
    new entry and serves it (``miss``).
  * Stale entry while another worker holds the lock: the previous copy is served
    (``stale``) instead of stacking a second multi-second render behind the
    first — the new version lands the moment that render finishes.

**Compression is paid once.** A stored entry keeps a gzip copy of the body beside
the plain one and a hit answers a gzip-accepting client with it directly, so
``GZipMiddleware`` — which skips a response that already carries a
``Content-Encoding`` — does not recompress megabytes of HTML on every request.
Its per-response random padding (the BREACH mitigation) is not applied to that
copy; it protects secrets reflected beside attacker-controlled input, and a
stored page carries neither: a CSRF token is refused below and a query string
never reaches a slot.

**What is never stored.** Anything but a plain ``200``, a streaming response, a
response that set its own ``Cache-Control: private``/``no-store``, and any render
that produced a CSRF token. A token printed into the HTML belongs to one visitor,
and handing it to the next would fail their form; a page that needs one in its
markup is not a page for this cache (see ``keel_web.csrf_defer`` for the way out).
"""

from __future__ import annotations

import gzip
import hashlib
from collections.abc import Callable

from django.core.cache import caches
from django.db import connections, router
from django.http import HttpRequest, HttpResponse
from django.utils.cache import cc_delim_re, patch_vary_headers
from django.utils.regex_helper import _lazy_re_compile

HEADER = "X-Keel-Page-Cache"
DEFAULT_TIMEOUT = 7 * 24 * 60 * 60
DEFAULT_LOCK_SECONDS = 120

_POSTGRES_SQL = (
    "SELECT count(*), md5(coalesce(string_agg(xmin::text || ':' || ctid::text, ',' "
    "ORDER BY ctid), '')) FROM {table}"
)
_GENERIC_SQL = "SELECT count(*), max({pk}) FROM {table}"
_ACCEPTS_GZIP = _lazy_re_compile(r"\bgzip\b")


def data_fingerprint(*models) -> str:
    """A short digest that changes whenever a row of any of ``models`` is written.

    Each model is read on the database its router sends reads to, and the
    database name is part of the digest, so two databases behind one cache
    (a test run beside development, say) never produce the same value.
    """
    parts = []
    for model in models:
        alias = router.db_for_read(model)
        connection = connections[alias]
        table = connection.ops.quote_name(model._meta.db_table)
        if connection.vendor == "postgresql":
            sql = _POSTGRES_SQL.format(table=table)
        else:
            pk = connection.ops.quote_name(model._meta.pk.column)
            sql = _GENERIC_SQL.format(table=table, pk=pk)
        with connection.cursor() as cursor:
            cursor.execute(sql)
            count, digest = cursor.fetchone()
        name = connection.settings_dict.get("NAME")
        parts.append(f"{alias}:{name}:{model._meta.db_table}:{count}:{digest}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


def cached_page(
    request: HttpRequest,
    *,
    slot: str,
    version: str,
    render: Callable[[], HttpResponse],
    cache_alias: str = "default",
    timeout: int = DEFAULT_TIMEOUT,
    lock_seconds: int = DEFAULT_LOCK_SECONDS,
) -> HttpResponse:
    """Return the page stored for ``slot`` at ``version``, rendering it when needed.

    ``render`` is called with no arguments and must return the response the view
    would have returned without this cache. See the module docstring for what a
    slot must separate and for when the stored copy is served stale.
    """
    cache = caches[cache_alias]
    entry_key = "keel_web:page:" + hashlib.sha256(slot.encode()).hexdigest()
    lock_key = entry_key + ":lock"

    entry = cache.get(entry_key)
    if entry and entry.get("version") == version:
        return _from_entry(request, entry, "hit")

    if not cache.add(lock_key, version, lock_seconds):
        if entry:
            return _from_entry(request, entry, "stale")
        response = render()
        response[HEADER] = "miss"
        return response

    try:
        response = render()
        if _storable(request, response):
            cache.set(
                entry_key,
                {
                    "version": version,
                    "content": response.content,
                    "gzip": gzip.compress(response.content, compresslevel=9, mtime=0),
                    "content_type": response.get("Content-Type"),
                },
                timeout,
            )
    finally:
        cache.delete(lock_key)
    response[HEADER] = "miss"
    return response


def _from_entry(request: HttpRequest, entry: dict, state: str) -> HttpResponse:
    compressed = entry.get("gzip")
    if compressed and _ACCEPTS_GZIP.search(request.META.get("HTTP_ACCEPT_ENCODING", "")):
        response = HttpResponse(compressed, content_type=entry["content_type"])
        response["Content-Encoding"] = "gzip"
    else:
        response = HttpResponse(entry["content"], content_type=entry["content_type"])
    patch_vary_headers(response, ("Accept-Encoding",))
    response[HEADER] = state
    return response


def _storable(request: HttpRequest, response: HttpResponse) -> bool:
    if response.status_code != 200 or getattr(response, "streaming", False):
        return False
    directives = {
        d.strip().split("=", 1)[0].lower()
        for d in cc_delim_re.split(response.get("Cache-Control", ""))
        if d.strip()
    }
    if directives & {"private", "no-store"}:
        return False
    # get_token() marks the request whenever a render asked for a CSRF token.
    if request.META.get("CSRF_COOKIE_NEEDS_UPDATE"):
        return False
    return True
