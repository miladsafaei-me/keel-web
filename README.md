# keel-web

Reusable web-app foundation for Keel projects — the **auth foundation**, the
**staff-panel shell**, and the **client-panel shell**. Extracted from SignalBots
and neutralized: every project-specific piece is a config hook or a template
block, not hardcoded.

Read [`PLATFORM.md`](https://github.com/miladsafaei-me/keel-kit) (in keel-kit) for
the platform model, and this repo's [`CLAUDE.md`](CLAUDE.md) for the contract.

## Three namespaced Django apps (install what you need)

| App label | Module | What it provides |
|---|---|---|
| `keel_web_auth` | `keel_web.auth` | Custom `User` foundation (`AbstractKeelUser` + a concrete swappable `User`), `SingleSessionMiddleware` + login signal, allauth `Account`/`SocialAccount` adapters, branded transactional email helpers, the `account_status` context processor, the persona-avatar catalogue, phone parsing/validation, the four account-settings forms, and the shared `{% load keel_icons %}` inline-SVG icon set. |
| `keel_web_admin` | `keel_web.admin_shell` | TailAdmin staff-panel chrome (`base_admin.html`, `_sidebar`, `_navbar`, the 3-tab content editor partials), permission mixins, the generic nav active-state resolver, the Gemini image-generation HTTP core, and the Pillow→WebP image-upload helper. |
| `keel_web_client` | `keel_web.client` | Client-panel shell (`base_client.html` + partials, profile/settings + persona builder, billing stub, resend-verification), the `NavItem`/`NavSection` dataclasses + nav resolver, the `client_extras` template tags, and the shared TailAdmin CSS/JS bundle. |

`keel_web.storage.KeelManifestStaticFilesStorage` (manifest static + in-place
CSS/JS minify) is a top-level module usable on its own, as is
`keel_web.cache.AnonymousPageCacheMiddleware` (edge-cacheable anonymous public
pages — see below).

A fourth, minimal app — `keel_web_csrf` / `keel_web.csrf_defer` — ships the
deferred-CSRF token endpoint and its JS helper (also below). It has no models
and no dependency on the other three apps.

## What stays in the host (Bucket-0 — NOT here)

The coupon / purchase / lead models + `record_web_lead`, the concrete `CLIENT_NAV`
instance, every trading / signals / affiliate / onboarding page + view, the
product/market/licensing/Telegram-robot admin, the AI-settings field list, and the
orphaned Gemini FOREX system-prompt `.txt`. keel-web imports none of them; where the
original reached into them, there is now a config hook.

## Consume it (host wiring — this is the WIRE step, done per host)

1. `pip install keel-web` (or a git/editable install during development).
2. Add the app(s) to `INSTALLED_APPS`: `keel_web.auth`, `keel_web.admin_shell`,
   `keel_web.client` (each declares its own collision-safe label).
3. Choose one of two user-model paths:
   - **Fresh project:** add `keel_web.auth` to `INSTALLED_APPS` and point
     `AUTH_USER_MODEL = "keel_web_auth.User"` (optionally set
     `KEEL_WEB["user_db_table"]` to reuse an existing table name).
   - **Adopt an existing user table (no `AUTH_USER_MODEL` swap):** keep your own
     concrete `User` and subclass the abstract base —
     `from keel_web.auth.base import AbstractKeelUser`. `base.py` defines **no**
     concrete model, so you do **not** install `keel_web.auth` (installing it
     would register keel-web's own concrete `User`, whose `groups`/
     `user_permissions` reverse accessors then clash with yours). Your existing
     `AUTH_USER_MODEL` + table are untouched; `user_db_table` is irrelevant on
     this path. This is how SignalBots consumes keel-web (its `W3` wire).
4. Wire allauth: `ACCOUNT_ADAPTER = "keel_web.auth.adapters.AccountAdapter"`,
   `SOCIALACCOUNT_ADAPTER = "keel_web.auth.adapters.SocialAccountAdapter"`.
5. Add `keel_web.auth.middleware.SingleSessionMiddleware` to `MIDDLEWARE` and
   `keel_web.auth.context_processors.account_status` to your context processors.
6. `STATICFILES_STORAGE = "keel_web.storage.KeelManifestStaticFilesStorage"`.
7. Mount the client shell routes: `path("client/", include("keel_web.client.urls", namespace="client"))`
   and add your own product routes (dashboard, etc.) under the same namespace.
8. Configure via `KEEL_WEB` (all optional — see `keel_web/config.py`).
9. Optional: to let a CDN cache anonymous public pages at the edge, add
   `keel_web.cache.AnonymousPageCacheMiddleware` to `MIDDLEWARE` **directly
   after** `django.contrib.sessions.middleware.SessionMiddleware`, and set
   `KEEL_WEB["anonymous_page_cache"]["enabled"] = True`. See
   [Anonymous page caching](#anonymous-page-caching-keel_webcache) below.
10. Optional: if step 9 is otherwise blocked by a page's own `{% csrf_token %}`
    (a newsletter box, a header search field), add `"keel_web.csrf_defer"` to
    `INSTALLED_APPS` and `path("", include("keel_web.csrf_defer.urls"))` to the
    root URLconf. See
    [Deferred CSRF](#deferred-csrf-keel_webcsrf_defer) below.
11. Optional: for a public page that takes seconds to build from data that changes
    rarely, call `keel_web.page_cache.cached_page` from its view. No settings key;
    see [Page cache](#page-cache-keel_webpage_cache) below.

## Config-contract / override seams (`KEEL_WEB`)

| Key | Default | Host provides |
|---|---|---|
| `user_db_table` | `keel_web_auth_user` | existing user table to adopt |
| `content_editor_group` | `Content Editor` | the group that gates the CMS + panel switch |
| `permission_denied_redirect` | `home` | named URL a denied staff request lands on |
| `client_path_prefix` | `/client/` | prefix that scopes the email-verify banner |
| `signup_lead_hook` | none | `fn(*, user, product_key, request)` for gated signups |
| `client_nav` | empty | dotted path to a `NavSection` tuple (or callable) |
| `client_base_context_hook` | none | `fn(request) -> dict` merged into every client view |
| `email_logo_static` | `img/email/logo.png` | the transactional-email logo path |
| `static_skip_hash_prefixes` / `static_minify_skip_substrings` | Tailwind-safe defaults | storage tuning |
| `image_gen.*_hook` | env defaults | API key / endpoint / aspect / system-instruction resolvers |
| `anonymous_page_cache.*` | off (see below) | edge-cacheability for anonymous public GET/HEAD — see [Anonymous page caching](#anonymous-page-caching-keel_webcache) |
| `api_guard.*` | off (see below) | keep `/api/` endpoints to the site's own pages — see [API guard](#api-guard-keel_webapi_guard) |

Templates expose blocks for the rest: `panel_logo`, `panel_banner`,
`brand_suffix`, `favicon`, `head_extra`, plus the client `admin_home_url` context
var for the staff-panel switch link.

## Anonymous page caching (`keel_web.cache`)

A Cloudflare Cache Rule (or any shared/edge cache) that caches HTML refuses to
cache a response carrying `Set-Cookie` or an uncacheable `Vary`. Most Django
sites emit exactly that on every first-touch anonymous GET, because *something*
global in the middleware stack writes to the session — the confirmed case is
django-machina's `ForumPermissionMiddleware`, which runs on every request, not
just `/forum/`, but any project can have its own equivalent cause. The result:
a crawler, which never returns with a cookie jar, pays full uncached origin
cost on every fetch of every public URL. `AnonymousPageCacheMiddleware`
neutralizes that for requests that are genuinely anonymous reads of a public
page, and changes nothing at all for any other request. Full mechanism, the
exact `MIDDLEWARE` position requirement, and every eligibility rule are in the
`keel_web/cache.py` module docstring.

Wiring:

```python
MIDDLEWARE = [
    ...,
    "django.contrib.sessions.middleware.SessionMiddleware",
    "keel_web.cache.AnonymousPageCacheMiddleware",  # directly after SessionMiddleware
    ...,
]

KEEL_WEB = {
    "anonymous_page_cache": {
        "enabled": True,
        "exempt_prefixes": ("/admin", "/accounts", "/client"),  # add your own (forum, etc.)
        "browser_max_age": 300,
        "edge_max_age": 3600,
        "stale_while_revalidate": None,  # e.g. 86400 beside a short edge_max_age
        "vary_drop": (),            # e.g. ("Accept-Language",) on a single-language site
        "drop_csrf_cookie": False,  # leave off unless a page's only cookie is a CSRF token no form needs
    },
}
```

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `False` | Master switch. Off by default — installing/upgrading the package never changes a host's cache behaviour on its own. |
| `exempt_prefixes` | `("/admin", "/accounts", "/client")` | Path prefixes left completely untouched. Extend, don't replace, for a host's own session-requiring areas (forum, checkout, …). |
| `browser_max_age` | `300` | `Cache-Control: max-age=` (seconds), the browser-cache lifetime. |
| `edge_max_age` | `3600` | `Cache-Control: s-maxage=` (seconds), the shared/edge-cache lifetime. |
| `stale_while_revalidate` | `None` | `Cache-Control: stale-while-revalidate=` (seconds), omitted when unset. An edge that honours it keeps answering from its copy while it refetches in the background, so a short `edge_max_age` stops costing visitors an origin round trip each time it lapses. |
| `vary_drop` | `()` | `Vary` field names to strip (case-insensitive), e.g. `("Accept-Language",)` on a site serving one language from every URL. Opt-in per field — never drop one a site's URLs genuinely vary on. |
| `drop_csrf_cookie` | `False` | Strip a CSRF cookie from an otherwise-eligible response. Off by default because a page with a real POST form needs that cookie; the better fix for a page that only renders `{% csrf_token %}` in a GET-only form is usually to stop rendering the token there. |

Even with every key configured, a response that still carries any
`Set-Cookie` after the session no-op and the optional CSRF-cookie drop is
never marked cacheable — serving one visitor's cookie to another is the one
failure this middleware exists to prevent, so that check cannot be turned off.

## Page cache (`keel_web.page_cache`)

The middleware above lets an edge keep a page; this keeps the origin from rebuilding
one. A view whose page takes seconds of Python — a ranked board, a homepage that
reads a whole roster — hands its render to `cached_page`, which serves a stored copy
until the data behind it changes:

```python
from datetime import date

from keel_web.page_cache import cached_page, data_fingerprint


def home(request):
    viewer = "staff" if request.user.is_staff else "public"
    return cached_page(
        request,
        slot=f"home:{viewer}:{request.scheme}://{request.get_host()}",
        version=f"{settings.RELEASE_VERSION}:{date.today()}:{data_fingerprint(Firm, Landing)}",
        render=lambda: render(request, "home.html", build_context()),
    )
```

- **`data_fingerprint(*models)`** digests every row version of those tables. On
  PostgreSQL it reads `xmin` and `ctid`, so it moves on every write path —
  `save(update_fields=...)` that skips `updated_at`, `QuerySet.update()`, raw SQL — in
  well under a millisecond. Other databases fall back to count and highest primary key,
  which misses updates.
- **`slot`** separates renders that differ. Everything about the viewer that changes the
  HTML belongs in it; nothing else is read. Render query-string requests directly
  rather than keying on the string.
- **`version`** is everything that invalidates: the fingerprint, the release, the date
  when the page prints one.
- A stale copy is served (`X-Keel-Page-Cache: stale`) while one worker renders the new
  one, so a data change costs one render rather than one per concurrent request. A stored
  page keeps a gzip copy, so a hit is not recompressed.
- Never stored: a non-200, a streaming or `private`/`no-store` response, and any render
  that produced a CSRF token. Full reasoning in the module docstring.

## Front-end delivery (`keel_web.frontend`)

Four Lighthouse findings come back on every new page unless the shared layer prevents
them: a stylesheet linked per file (each one a render-blocking round trip), the whole Font
Awesome stylesheet and three full webfonts for a few dozen icons, `font-display: block` on
those fonts, and a large PNG drawn in a small box. `keel_web.frontend` removes all four at
the layer every page already goes through. Install `"keel_web.frontend"` and the
`keel-web[frontend]` extra (fonttools for the subset).

```python
KEEL_WEB = {
    "frontend": {
        "enabled": BUILT_IN_THIS_IMAGE,          # False: link sources and stock Font Awesome
        "output_dir": BASE_DIR / "core/static",  # a directory a staticfiles finder serves
        "bundle_dir": "keel_frontend",
        "css_bundles": {
            "site": ["vendor/fonts/inter/inter.css", "keel_frontend/icons/fa-subset.css", "css/base.css"],
            "home": ["css/pages/home.css"],
        },
        "icons": {"css": "vendor/font-awesome/6.4.0/css/all.min.css", "scan_roots": [str(BASE_DIR)]},
    },
}
```

- **`manage.py build_frontend_assets`** runs before `collectstatic` (the image build): it
  scans `scan_roots` for `fa-*` names, writes a subset stylesheet (unused icon rules gone,
  faces pointed at subset fonts with `font-display: swap`) and subset WOFF2 files, then
  concatenates each bundle with relative `url()`s rebased. `--check` only verifies sources.
- **`{% css_bundle "site" %}`** links the built bundle when `enabled` and the file exists,
  otherwise every source (the icon subset falls back to the stock stylesheet), so an
  unbuilt tree always renders.
- **`{% icon_font_preload %}`** preloads the solid icon font actually in use.
- **`{% media_img url 48 48 class="logo" alt="" %}`** writes an `<img>` whose `src` is a
  WebP at the box width and whose `srcset` adds 2x, generated once beside the source under
  `_v/` with a name that changes when the source does. Non-media, SVG, external and missing
  files pass through. Serve `_v/` files with `images.cache_control_for(path, default)`.

An icon class assembled at runtime, or stored in database content, is invisible to the
scan and renders as nothing; keep icon names literal.

## Deferred CSRF (`keel_web.csrf_defer`)

`AnonymousPageCacheMiddleware` above fixes the *session*-cookie half of edge
cacheability. It cannot fix the other common cause of an uncacheable
`Set-Cookie`: a page that renders `{% csrf_token %}` for a form that is merely
incidental to that page — a newsletter signup, a header search box — makes
Django set a CSRF cookie on *every* response that includes it, even though
nothing about the page is personalised. Dropping that cookie
(`drop_csrf_cookie` above) would just break the form. `keel_web.csrf_defer` is
the real fix: the page ships with **no** token and **no** CSRF cookie at all,
and the token is fetched on demand, just before the form actually submits.

**Only use this for a form that is incidental to the page.** A page whose
*purpose* is the form — login, signup, checkout — should keep the ordinary
`{% csrf_token %}` and simply not be cached. Full trade-off explanation:
`keel_web/csrf_defer/views.py` module docstring.

Wiring — the exact same recipe on every consumer:

1. Add `"keel_web.csrf_defer"` to `INSTALLED_APPS` (registers the
   `keel_web_csrf` static namespace; no models, no migrations).
2. Mount the URL fragment, unmodified, at the root of the URLconf:

   ```python
   urlpatterns = [
       ...,
       path("", include("keel_web.csrf_defer.urls")),
       ...,
   ]
   ```

   This puts the endpoint at `/csrf-token/` — the same path on every
   consumer, because the JS helper below hardcodes it too.
3. In the template, drop `{% csrf_token %}` from the incidental form and add
   the marker attribute + an empty hidden field instead:

   ```html
   <form method="post" action="{% url 'newsletter_signup' %}" data-keel-deferred-csrf>
     <input type="hidden" name="csrfmiddlewaretoken" value="">
     <input type="email" name="email">
     <button type="submit">Subscribe</button>
   </form>
   ```

4. Load the JS helper through the host's normal static/css-bundles pipeline
   (never an inline `<script>` block):

   ```html
   <script src="{% static 'keel_web_csrf/js/deferred-csrf.js' %}"></script>
   ```

No `KEEL_WEB` settings key exists for this feature — the endpoint path is
fixed on purpose so every consumer agrees with the JS helper without any
per-host configuration.

## API guard (`keel_web.api_guard`)

An endpoint a page fetches — a JSON list, an HTML fragment behind a filter — is a URL
like any other: a crawler can index it, an edge cache can store one caller's answer and
hand it to the next, and a script can pull the whole dataset behind it without loading a
page. `ApiGuardMiddleware` answers a request under a guarded prefix only when it comes
from the site's own pages (`Sec-Fetch-Site: same-origin`, or an `Origin`/`Referer` on this
host), from a configured trusted origin, or with a configured bearer token, and refuses the
rest with a 403. Every guarded response, answered or refused, carries
`X-Robots-Tag: noindex` and `Cache-Control: private, no-store`.

Browser headers keep other sites' pages out; they do not stop a program that copies them.
Only a token is a grant. Full mechanism: the `keel_web/api_guard.py` module docstring.

Wiring:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "keel_web.api_guard.ApiGuardMiddleware",  # above anything that writes Cache-Control
    ...,
]

KEEL_WEB = {
    "api_guard": {
        "enabled": True,
        "prefixes": ("/api/",),
        "trusted_origins": (),  # e.g. ("https://partner.example",)
        "access_tokens": tuple(t for t in os.environ.get("API_ACCESS_TOKENS", "").split(",") if t),
        "robots": "noindex",
    },
}
```

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `False` | Master switch; upgrading the package changes nothing until a host turns it on. |
| `prefixes` | `("/api/",)` | Path prefixes the guard covers. |
| `trusted_origins` | `()` | Origins (`scheme://host`) whose pages may call a guarded endpoint from a browser. |
| `access_tokens` | `()` | Bearer tokens (`Authorization: Bearer <token>`) that grant any caller access. |
| `robots` | `"noindex"` | The `X-Robots-Tag` value on every guarded response. |

## Status

v0.3.0 — extracted, neutralized, and consumed by SignalBots (its first host): the
custom `User` is adopted by subclassing `AbstractKeelUser` (no `AUTH_USER_MODEL`
swap), single-session middleware, the allauth adapters, the transactional-email
chrome, the staff/client panel shells, the `.xlsx` export helper, anonymous
edge-page caching, and deferred CSRF are all live.
