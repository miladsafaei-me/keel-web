"""Tests for keel_web.geo_block -- GeoBlockMiddleware.

Run: DJANGO_SETTINGS_MODULE=tests.settings python -m django test tests.test_geo_block
"""
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings

from keel_web import geo_block
from keel_web.config import geo_block_setting

PAGE = "/page/"
GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
CRAWLER_IP = "66.249.66.1"


def keel_web_with(**geo):
    config = dict(settings.KEEL_WEB)
    config["geo_block"] = {"enabled": True, "countries": ("TR", "in"), **geo}
    return override_settings(KEEL_WEB=config)


class DefaultConfigTests(TestCase):
    def test_the_block_is_off_by_default(self):
        with override_settings(KEEL_WEB={}):
            self.assertFalse(geo_block_setting("enabled"))
            response = self.client.get(PAGE, HTTP_CF_IPCOUNTRY="TR")
        self.assertEqual(response.status_code, 200)


@keel_web_with()
class GeoBlockTests(TestCase):
    def setUp(self):
        cache.clear()

    def assert_refused(self, response):
        self.assertEqual(response.status_code, 451)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Robots-Tag"], "noindex")

    def test_a_visitor_from_a_blocked_country_is_refused(self):
        self.assert_refused(self.client.get(PAGE, HTTP_CF_IPCOUNTRY="TR"))

    def test_country_codes_are_matched_case_insensitively(self):
        self.assert_refused(self.client.get(PAGE, HTTP_CF_IPCOUNTRY="in"))

    def test_every_method_is_refused(self):
        self.assert_refused(self.client.head(PAGE, HTTP_CF_IPCOUNTRY="TR"))
        self.assert_refused(self.client.post(PAGE, HTTP_CF_IPCOUNTRY="TR"))

    def test_a_visitor_from_another_country_is_served_but_never_edge_cached(self):
        response = self.client.get(PAGE, HTTP_CF_IPCOUNTRY="MY")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("public", response["Cache-Control"])
        self.assertNotIn("s-maxage", response["Cache-Control"])
        self.assertIn("private", response["Cache-Control"])

    def test_a_request_with_no_country_header_is_served(self):
        self.assertEqual(self.client.get(PAGE).status_code, 200)

    def test_an_exempt_prefix_is_served_from_a_blocked_country(self):
        self.assertEqual(self.client.get("/admin/dashboard/", HTTP_CF_IPCOUNTRY="TR").status_code, 200)

    def test_signed_in_staff_is_served_from_a_blocked_country(self):
        response = self.client.get(PAGE, HTTP_CF_IPCOUNTRY="TR", HTTP_X_FAKE_STAFF="1")
        self.assertEqual(response.status_code, 200)

    def test_a_crawler_user_agent_alone_is_refused(self):
        with mock.patch.object(geo_block.socket, "gethostbyaddr", side_effect=OSError):
            response = self.client.get(
                PAGE, HTTP_CF_IPCOUNTRY="TR", HTTP_USER_AGENT=GOOGLEBOT, HTTP_CF_CONNECTING_IP="203.0.113.9"
            )
        self.assert_refused(response)

    def test_a_crawler_on_a_lookalike_domain_is_refused(self):
        with mock.patch.object(geo_block.socket, "gethostbyaddr", return_value=("crawl.notgooglebot.com", [], [])):
            response = self.client.get(
                PAGE, HTTP_CF_IPCOUNTRY="TR", HTTP_USER_AGENT=GOOGLEBOT, HTTP_CF_CONNECTING_IP="203.0.113.9"
            )
        self.assert_refused(response)

    def test_a_crawler_whose_name_does_not_resolve_back_is_refused(self):
        with mock.patch.object(
            geo_block.socket, "gethostbyaddr", return_value=("crawl-66-249-66-1.googlebot.com", [], [])
        ), mock.patch.object(geo_block.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("198.51.100.1", 0))]):
            response = self.client.get(
                PAGE, HTTP_CF_IPCOUNTRY="TR", HTTP_USER_AGENT=GOOGLEBOT, HTTP_CF_CONNECTING_IP=CRAWLER_IP
            )
        self.assert_refused(response)

    def test_a_dns_verified_crawler_is_served_and_the_verdict_is_cached(self):
        with mock.patch.object(
            geo_block.socket, "gethostbyaddr", return_value=("crawl-66-249-66-1.googlebot.com", [], [])
        ) as reverse, mock.patch.object(
            geo_block.socket, "getaddrinfo", return_value=[(2, 1, 6, "", (CRAWLER_IP, 0))]
        ):
            for _ in range(2):
                response = self.client.get(
                    PAGE, HTTP_CF_IPCOUNTRY="TR", HTTP_USER_AGENT=GOOGLEBOT, HTTP_CF_CONNECTING_IP=CRAWLER_IP
                )
                self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse.call_count, 1)

    def test_the_anonymous_page_cache_never_marks_a_page_public(self):
        response = self.client.get("/vary-page/", HTTP_CF_IPCOUNTRY="MY")
        self.assertNotIn("public", response.get("Cache-Control", ""))

    def test_an_explicit_no_store_is_left_alone(self):
        response = self.client.get("/no-store/", HTTP_CF_IPCOUNTRY="MY")
        self.assertEqual(response["Cache-Control"], "no-store")


@keel_web_with(shared_cache=True)
class SharedCacheTests(TestCase):
    def test_edge_caching_survives_when_the_edge_blocks_too(self):
        response = self.client.get(PAGE, HTTP_CF_IPCOUNTRY="MY")
        self.assertIn("public", response["Cache-Control"])


@keel_web_with(template="hostapp/page.html")
class TemplateTests(TestCase):
    def test_the_host_template_renders_the_refusal(self):
        response = self.client.get(PAGE, HTTP_CF_IPCOUNTRY="TR")
        self.assertEqual(response.status_code, 451)
        self.assertNotIn(b"Not available in your country", response.content)


class KeepOutOfSharedCachesTests(TestCase):
    def rewrite(self, header):
        from django.http import HttpResponse

        response = HttpResponse()
        if header is not None:
            response["Cache-Control"] = header
        with keel_web_with(browser_max_age=60):
            geo_block._keep_out_of_shared_caches(response)
        return response["Cache-Control"]

    def test_public_edge_directives_become_private(self):
        self.assertEqual(
            self.rewrite("public, max-age=300, s-maxage=3600, stale-while-revalidate=60"), "private, max-age=300"
        )

    def test_a_missing_header_becomes_private(self):
        self.assertEqual(self.rewrite(None), "private, max-age=60")

    def test_a_private_header_is_unchanged(self):
        self.assertEqual(self.rewrite("private, max-age=10"), "private, max-age=10")
