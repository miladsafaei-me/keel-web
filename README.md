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
CSS/JS minify) is a top-level module usable on its own.

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

Templates expose blocks for the rest: `panel_logo`, `panel_banner`,
`brand_suffix`, `favicon`, `head_extra`, plus the client `admin_home_url` context
var for the staff-panel switch link.

## Status

v0.1.0 — Python core + shell templates/static extracted and neutralized;
self-validated by compile + coupling inspection. Live wiring into a host
(user-model migration + settings + parity on `localhost:8082`) is the host's WIRE
step (`W3`).
