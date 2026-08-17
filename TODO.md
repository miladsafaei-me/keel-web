# TODO

This file is the single source of truth for pending, follow-up, and deferred work on this project. See CLAUDE.md for the tracking rule.

Guidelines:
- Add a task here as soon as it's identified — with priority, prerequisites/dependencies, and enough context to pick it up cold.
- Group by priority: P0 (urgent / blocking / production risk), P1 (next up), P2 (backlog / nice-to-have).
- Note real dependencies explicitly ("Blocked by: ...", "Requires: ...").
- Delete a task from this file the moment it's done. This file only ever holds what's left.

## P1 — Next up
- [ ] **Media-serving helper for `DEBUG=False` behind a tunnel/no-nginx deploy.** `django.conf.urls.static.static()` returns `[]` whenever `DEBUG=False`, so the common `if DEBUG: urlpatterns += static(...)` idiom never registers `/media/` in production — every uploaded image 404s when there's no nginx in front (Cloudflare Tunnel → gunicorn on loopback). This fix is currently duplicated by hand in each consumer's `config/urls.py` (revenika fixed 2026-07-30; martiland/propopedia/binaryoptiontrading still exposed or unverified). Add a keel-web helper — e.g. `keel_web.urls.media_urlpatterns()` or similar — that registers `re_path(r"^media/(?P<path>.*)$", django.views.static.serve, {"document_root": MEDIA_ROOT})` when `DJANGO_SERVE_MEDIA=1` and not `DEBUG`, so hosts call one function instead of copy-pasting the pattern. Update README's config-contract table once shipped, and note it in a consumer as the reference wiring.
- [ ] **Shared HTTPS-behind-proxy settings helper.** Every consumer behind the Cloudflare tunnel hand-writes the same two settings: `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` and `CSRF_TRUSTED_ORIGINS` derived from `ALLOWED_HOSTS` (plus secure cookies when not `DEBUG`). Add a keel-web settings helper (e.g. `keel_web.config.proxy_settings(allowed_hosts)` returning a dict to merge into `settings.py`, or a documented snippet in `config.py`) so this isn't reproduced per project. Verify against current martiland/revenika `settings.py` before writing — confirm the exact shape still in use (note: do NOT set an env var that forces `SECURE_SSL_REDIRECT`, since that 301s the loopback health check and aborts deploys, per revenika's `DJANGO_USE_TLS` gotcha).

## P2 — Backlog
- [ ] No `CHANGELOG.md` exists despite a version-guard CI that enforces version bumps on `src/` changes — consider adding one so releases have a human-readable history (currently only `git log` + commit-message trailers).
- [ ] No test suite in the repo (`find . -name "test*"` turns up nothing) — the version guard checks version discipline only, not behavior. Consider at least smoke tests for `keel_web.storage.KeelManifestStaticFilesStorage` and `keel_web.exports.write_xlsx` (pure-Python, no Django app under test needed for the latter).
- [ ] README "Status" section still says "v0.1.2 — extracted, neutralized, and consumed by SignalBots" while `pyproject.toml` is at 0.1.4 and two features shipped since (0.1.3 exports/.xlsx writer, and the 0.1.2→0.1.3 admin_shell self-sufficiency work for non-auth CMS hosts, e.g. keel-cms). Update the Status line and the app table to mention `keel_web.exports` and the admin_shell auth-optional path.
