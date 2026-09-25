# keel-web — package guide

Part of the **Keel** platform (see keel-kit `PLATFORM.md`). Three Bucket-2/3
reusable Django apps + a static-storage module: the auth foundation, the staff
panel shell, and the client panel shell. English only; no banner comments; CSS
variables only in any styling; multi-line Django template comments use
`{% comment %}…{% endcomment %}` (never multi-line `{# … #}`).

## Task tracking

Remaining and follow-up work for this project is tracked in [TODO.md](TODO.md), not in chat memory. Every pending task — priority, prerequisites/dependencies, enough context to resume cold — goes there before starting new work; remove a task from TODO.md the moment it's done.

## Boundaries — what is here vs what stays in the host

- **Here (generic):**
  - `keel_web.auth` — `AbstractKeelUser` + concrete `User`, `SingleSessionMiddleware`
    + login signal, allauth adapters (with the lead hook gated), branded email
    helpers, `account_status`, persona catalogue, phone helpers, the four
    account-settings forms, the `keel_icons` tag set.
  - `keel_web.admin_shell` — TailAdmin chrome (`base_admin`/`base`/`_sidebar`/`_navbar`),
    the field-agnostic 3-tab content editor partials, permission mixins,
    `resolve_nav_active`, the Gemini image-gen HTTP/decode/retry core, the WebP
    image-upload helper, and the admin CSS/JS.
  - `keel_web.client` — `base_client` + partials, profile/settings + persona
    builder + billing stub + resend-verification, `NavItem`/`NavSection` +
    `resolve_client_nav`, `client_extras` tags, the shared TailAdmin CSS/JS bundle.
  - `keel_web.storage.KeelManifestStaticFilesStorage`.
  - `keel_web.cache.AnonymousPageCacheMiddleware` — makes an anonymous GET/HEAD
    of a public page edge-cacheable (no `Set-Cookie`, no uncacheable `Vary`,
    a `Cache-Control` header) without touching any other request. Off by
    default (`KEEL_WEB["anonymous_page_cache"]["enabled"]`).
  - `keel_web.page_cache` — `cached_page` + `data_fingerprint`: serves an expensive
    page from the Django cache until a row of the tables it reads is written (by
    PostgreSQL row version), with a render lock that serves the previous copy while
    one worker re-renders. The host chooses the slot (who sees the same HTML) and the
    version (release, date); no `KEEL_WEB` key.
  - `keel_web.frontend` — `build_frontend_assets` (CSS bundles + a Font Awesome subset
    cut to the icons the source names) and the `keel_frontend` tags `{% css_bundle %}`,
    `{% icon_font_preload %}` and `{% media_img %}` (WebP 1x/2x variants of media images).
    Configured by `KEEL_WEB["frontend"]`; off, it links sources and stock assets unchanged.
  - `keel_web.csrf_defer` — the deferred-CSRF token endpoint + JS helper: lets
    a page with an incidental form (newsletter, header search) ship with no
    CSRF cookie at all, so it stays eligible for the edge caching above. No
    `KEEL_WEB` key — the URL is fixed by design. See `keel_web/csrf_defer/views.py`
    module docstring for the mechanism and the trade-off, and README's
    "Deferred CSRF" section for the wiring recipe.
  - `keel_web.api_guard.ApiGuardMiddleware` — keeps `/api/` endpoints to the site's own
    pages: answers a same-origin browser fetch, a trusted origin or a bearer token,
    refuses the rest with a 403, and marks every guarded response `noindex` and
    `private, no-store`. Off by default (`KEEL_WEB["api_guard"]`).
  - `keel_web.geo_block.GeoBlockMiddleware` — answers 451 to a visitor whose
    `CF-IPCountry` names a configured country, serving admin/login prefixes, signed-in
    staff and DNS-verified search-engine crawlers from anywhere, and keeping every
    let-through response out of shared caches unless the edge blocks too. Off by default
    (`KEEL_WEB["geo_block"]`).
- **Stays in the host (Bucket-0):** coupon/purchase/lead models + `record_web_lead`
  (wired via `KEEL_WEB["signup_lead_hook"]`), the concrete `CLIENT_NAV` (wired via
  `KEEL_WEB["client_nav"]`), all trading/signals/affiliate/onboarding pages + views,
  the product/market/licensing/Telegram-robot admin, the AI-settings field list
  (image-gen resolvers come in via `KEEL_WEB["image_gen"]` hooks), and the orphaned
  Gemini FOREX system-prompt `.txt`.

## Editing rule (drift prevention)

When a consuming project has this installed, its copy of these files is **not**
editable in that project — change them **here**, bump the version, and let the
project pull the new version. Project-specific behaviour belongs in `KEEL_WEB`
config hooks or template blocks, never in a fork of this code.

## Namespacing contract (collision-safe)

Each app is a submodule of `keel_web` whose default label would collide with a
Django built-in (`auth`) or read ambiguously (`admin_shell`, `client`), so every
`AppConfig` sets an explicit `label` (`keel_web_auth`, `keel_web_admin`,
`keel_web_client`). Templates/static are namespaced under those labels
(`keel_web_client/…`, `keel_web_admin/…`). The staff shell reuses the client
CSS/JS bundle (`keel_web_client/css/client.css`, `…/vendor/alpine`), so a project
using only the staff panel still needs the `keel_web_client` static installed.

## Override hooks (config-contract) — see `keel_web/config.py`

The full table is in `README.md`. The seams, by area:

- **Auth:** `user_db_table` (adoption), `signup_lead_hook`, `content_editor_group`,
  `client_path_prefix`, `email_logo_static`, plus standard `BRAND_NAME` /
  `SITE_BASE_URL` / `DEFAULT_FROM_EMAIL`.
- **Staff panel:** `permission_denied_redirect`; the host builds its own nav data
  and calls `resolve_nav_active`; the content-editor partial reads endpoint URLs
  from context (`editor_convert_url`, `editor_upload_url`, `editor_ai_inline_url`,
  `editor_featured_url`, `editor_post_id`, `editor_is_pipeline`).
- **Client panel:** `client_nav`, `client_base_context_hook`; templates expose the
  `panel_logo` / `panel_banner` / `brand_suffix` / `favicon` / `head_extra` blocks
  and the `admin_home_url` context var.
- **Image gen:** `image_gen.api_key_hook` / `hero_url_hook` / `inline_url_hook` /
  `aspect_ratio_hook` / `hero_system_instruction_hook` / `inline_system_instruction_hook`
  — each with an env-style default so it works with zero hooks.
- **Storage:** `static_skip_hash_prefixes`, `static_minify_skip_substrings`.
- **Anonymous page cache:** `anonymous_page_cache.enabled` /
  `.exempt_prefixes` / `.browser_max_age` / `.edge_max_age` / `.vary_drop` /
  `.drop_csrf_cookie` — see `keel_web/cache.py` module docstring for the full
  mechanism and the required `MIDDLEWARE` position (directly after
  `SessionMiddleware`).
- **Deferred CSRF:** no config key. Install `keel_web.csrf_defer`, mount
  `keel_web.csrf_defer.urls` at the URLconf root (fixed path `/csrf-token/` on
  every consumer, on purpose), swap `{% csrf_token %}` for
  `data-keel-deferred-csrf` + a hidden `csrfmiddlewaretoken` input on the
  incidental form, and load `keel_web_csrf/js/deferred-csrf.js`.

## Adoption note (host migration — the delicate part of `W3`)

Two adoption paths (see README step 3). The **safe** one for a project that
already has a live user table is to **subclass, not swap**: keep your concrete
`User` and change its base to `AbstractKeelUser`, imported from
`keel_web.auth.base` (a module that defines **no** concrete model). Do **not** add
`keel_web.auth` to `INSTALLED_APPS` on this path — its own concrete `User` would
otherwise register and clash with yours on the `auth.Group`/`auth.Permission`
reverse accessors (`fields.E304`), and importing `keel_web.auth.models` (which
defines that concrete `User`) with the app uninstalled raises at import time —
hence the model-free `base.py`. `AUTH_USER_MODEL`, the table, and every existing
FK/migration stay exactly as they are; the field set matches, so `makemigrations`
is a no-op. Keep the host's own domain fields (coupons, purchases) alongside your
`User`. The alternative — installing `keel_web.auth` and pointing
`AUTH_USER_MODEL` at `keel_web_auth.User` with `user_db_table` — is a genuine
`AUTH_USER_MODEL` swap (swappable-dependency churn on every FK migration) and is
only worth it on a fresh or near-empty project. Either way: verify login,
single-session enforcement, and that the client + admin panels render before
cutover. SignalBots uses the subclass path (`W3`).

## The Tailwind build (client/admin chrome)

The panel chrome is TailAdmin v2 (Tailwind 4). `keel_web_client/tailwind/input.css`
is the source; `keel_web_client/css/client.css` is the built output that templates
load. Rebuild the output in the host after editing `input.css`; the storage backend
skips hashing the raw `tailwind/` source (`static_skip_hash_prefixes`).
