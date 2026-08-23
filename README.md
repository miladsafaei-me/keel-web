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
| `vary_drop` | `()` | `Vary` field names to strip (case-insensitive), e.g. `("Accept-Language",)` on a site serving one language from every URL. Opt-in per field — never drop one a site's URLs genuinely vary on. |
| `drop_csrf_cookie` | `False` | Strip a CSRF cookie from an otherwise-eligible response. Off by default because a page with a real POST form needs that cookie; the better fix for a page that only renders `{% csrf_token %}` in a GET-only form is usually to stop rendering the token there. |

Even with every key configured, a response that still carries any
`Set-Cookie` after the session no-op and the optional CSRF-cookie drop is
never marked cacheable — serving one visitor's cookie to another is the one
failure this middleware exists to prevent, so that check cannot be turned off.

## Status

v0.1.2 — extracted, neutralized, and consumed by SignalBots (its first host): the
custom `User` is adopted by subclassing `AbstractKeelUser` (no `AUTH_USER_MODEL`
swap), and single-session middleware, the allauth adapters, the transactional-email
chrome, and the staff/client panel shells are all live.
