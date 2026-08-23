"""Tests for keel_web.cache -- AnonymousPageCacheMiddleware.

Run: DJANGO_SETTINGS_MODULE=tests.settings python -m django test tests.test_cache
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings

from keel_web.config import anonymous_page_cache_setting


class DefaultConfigTests(TestCase):
    """The package-level default is off, with no Django settings involved."""

    def test_enabled_defaults_to_false(self):
        with override_settings(KEEL_WEB={}):
            self.assertFalse(anonymous_page_cache_setting("enabled"))


class AnonymousPageCacheMiddlewareTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_eligible_anonymous_get_becomes_cacheable(self):
        response = self.client.get("/page/")
        self.assertEqual(
            response["Cache-Control"], "public, max-age=300, s-maxage=3600"
        )
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
        self.assertNotIn("Set-Cookie", response.headers)
        vary = response.get("Vary", "")
        self.assertNotIn("Cookie", vary)

    def test_eligible_anonymous_head_becomes_cacheable(self):
        response = self.client.head("/page/")
        self.assertEqual(
            response["Cache-Control"], "public, max-age=300, s-maxage=3600"
        )

    def test_request_carrying_session_cookie_is_untouched(self):
        # Give the client an established (bogus) session cookie, as a
        # returning visitor would have.
        self.client.cookies[settings.SESSION_COOKIE_NAME] = "already-has-a-session"
        response = self.client.get("/page/")
        self.assertNotIn("Cache-Control", response.headers)
        # Django's normal session handling ran untouched: the session-writer
        # middleware's write was actually persisted, so a fresh Set-Cookie
        # comes back (the bogus key does not exist, so a new session/cookie
        # is issued) rather than being neutralized.
        self.assertIn(settings.SESSION_COOKIE_NAME, response.cookies)

    def test_authenticated_request_is_untouched(self):
        user = User.objects.create_user(username="alice", password="pw12345")
        self.client.force_login(user)
        response = self.client.get("/page/")
        self.assertNotIn("Cache-Control", response.headers)

    def test_authenticated_without_session_cookie_is_untouched(self):
        # Defensive guard: a non-session auth scheme can leave request.user
        # authenticated even with no session cookie on the request at all.
        response = self.client.get("/page/", HTTP_X_FAKE_TOKEN_AUTH="1")
        self.assertNotIn("Cache-Control", response.headers)

    def test_post_is_untouched(self):
        response = self.client.post("/page/", {})
        self.assertNotIn("Cache-Control", response.headers)

    def test_exempt_prefix_is_untouched(self):
        response = self.client.get("/admin/dashboard/")
        self.assertNotIn("Cache-Control", response.headers)

    def test_non_200_is_untouched(self):
        response = self.client.get("/broken/")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("Cache-Control", response.headers)

    def test_missing_route_404_is_untouched(self):
        response = self.client.get("/does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Cache-Control", response.headers)

    def test_view_explicit_no_store_survives(self):
        response = self.client.get("/no-store/")
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_configured_vary_field_removed_unconfigured_kept(self):
        overridden = {
            "anonymous_page_cache": {
                **settings.KEEL_WEB["anonymous_page_cache"],
                "vary_drop": ("Accept-Language",),
            }
        }
        with override_settings(KEEL_WEB=overridden):
            response = self.client.get("/vary-page/")
        self.assertEqual(response["Vary"], "X-Custom-Header")

    def test_unconfigured_vary_drop_leaves_vary_untouched(self):
        response = self.client.get("/vary-page/")
        self.assertEqual(response["Vary"], "Accept-Language, X-Custom-Header")

    def test_response_with_csrf_cookie_is_not_cached_by_default(self):
        response = self.client.get("/form-page/")
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
        self.assertNotIn("Cache-Control", response.headers)

    def test_drop_csrf_cookie_opt_in_allows_caching(self):
        overridden = {
            "anonymous_page_cache": {
                **settings.KEEL_WEB["anonymous_page_cache"],
                "drop_csrf_cookie": True,
            }
        }
        with override_settings(KEEL_WEB=overridden):
            response = self.client.get("/form-page/")
        self.assertNotIn(settings.CSRF_COOKIE_NAME, response.cookies)
        self.assertEqual(
            response["Cache-Control"], "public, max-age=300, s-maxage=3600"
        )

    def test_disabled_middleware_is_a_full_noop(self):
        overridden = {
            "anonymous_page_cache": {
                **settings.KEEL_WEB["anonymous_page_cache"],
                "enabled": False,
            }
        }
        with override_settings(KEEL_WEB=overridden):
            response = self.client.get("/page/")
        self.assertNotIn("Cache-Control", response.headers)
