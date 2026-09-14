"""Tests for keel_web.api_guard -- ApiGuardMiddleware.

Run: DJANGO_SETTINGS_MODULE=tests.settings python -m django test tests.test_api_guard
"""
from django.test import TestCase, override_settings

from keel_web.api_guard import REFUSAL
from keel_web.config import api_guard_setting

API = "/api/ping/"


class DefaultConfigTests(TestCase):
    def test_the_guard_is_off_by_default(self):
        with override_settings(KEEL_WEB={}):
            self.assertFalse(api_guard_setting("enabled"))
            response = self.client.get(API)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.has_header("X-Robots-Tag"))


class ApiGuardTests(TestCase):
    def assert_refused(self, response):
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": REFUSAL})
        self.assert_guarded_headers(response)

    def assert_guarded_headers(self, response):
        self.assertEqual(response["X-Robots-Tag"], "noindex")
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_a_request_that_names_no_page_is_refused(self):
        self.assert_refused(self.client.get(API))

    def test_a_fetch_from_this_origin_is_answered(self):
        response = self.client.get(API, HTTP_SEC_FETCH_SITE="same-origin")
        self.assertEqual(response.status_code, 200)
        self.assert_guarded_headers(response)

    def test_a_typed_address_is_refused(self):
        self.assert_refused(self.client.get(API, HTTP_SEC_FETCH_SITE="none"))

    def test_another_sites_page_is_refused(self):
        self.assert_refused(
            self.client.get(API, HTTP_SEC_FETCH_SITE="cross-site", HTTP_ORIGIN="https://elsewhere.example")
        )

    def test_a_referer_on_this_host_is_answered_without_fetch_metadata(self):
        response = self.client.get(API, HTTP_REFERER="http://testserver/page/")
        self.assertEqual(response.status_code, 200)

    def test_a_referer_on_another_host_is_refused(self):
        self.assert_refused(self.client.get(API, HTTP_REFERER="https://elsewhere.example/page/"))

    def test_a_trusted_origin_is_answered(self):
        response = self.client.get(API, HTTP_SEC_FETCH_SITE="cross-site", HTTP_ORIGIN="https://partner.example")
        self.assertEqual(response.status_code, 200)

    def test_a_granted_token_is_answered_and_any_other_refused(self):
        self.assertEqual(self.client.get(API, HTTP_AUTHORIZATION="Bearer granted-token").status_code, 200)
        self.assert_refused(self.client.get(API, HTTP_AUTHORIZATION="Bearer guessed-token"))
        self.assert_refused(self.client.get(API, HTTP_AUTHORIZATION="Bearer "))

    def test_an_answer_is_never_marked_shareable_by_the_page_cache(self):
        response = self.client.get(API, HTTP_SEC_FETCH_SITE="same-origin")
        self.assertNotIn("public", response["Cache-Control"])
        self.assertNotIn("s-maxage", response["Cache-Control"])

    def test_a_path_outside_the_prefix_is_untouched(self):
        response = self.client.get("/page/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.has_header("X-Robots-Tag"))
        self.assertIn("public", response["Cache-Control"])
