"""Tests for keel_web.csrf_defer -- deferred CSRF token endpoint.

Run: DJANGO_SETTINGS_MODULE=tests.settings python -m django test tests.test_csrf_defer
"""
from django.conf import settings
from django.test import Client, TestCase


class CsrfTokenViewTests(TestCase):
    """``enforce_csrf_checks=True`` -- the default test Client silently bypasses
    CSRF entirely, which would make every test here pass for the wrong reason.
    """

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_returns_token_and_sets_cookie(self):
        response = self.client.get("/csrf-token/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("csrfToken"))
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)

    def test_is_never_cacheable(self):
        response = self.client.get("/csrf-token/")
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_is_noindex(self):
        response = self.client.get("/csrf-token/")
        self.assertEqual(response["X-Robots-Tag"], "noindex")

    def test_two_fetches_each_set_a_usable_cookie(self):
        # A fresh visitor may hit this endpoint from more than one incidental
        # form on the same page load; neither fetch should break the other.
        first = self.client.get("/csrf-token/")
        second = self.client.get("/csrf-token/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)


class DeferredCsrfSubmitFlowTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_post_without_a_fetched_token_fails_csrf(self):
        response = self.client.post("/csrf-check/", {})
        self.assertEqual(response.status_code, 403)

    def test_post_with_wrong_token_still_fails_csrf(self):
        self.client.get("/csrf-token/")  # sets a valid cookie
        response = self.client.post(
            "/csrf-check/", {"csrfmiddlewaretoken": "not-the-real-token"}
        )
        self.assertEqual(response.status_code, 403)

    def test_post_with_token_fetched_from_the_endpoint_passes_csrf(self):
        token_response = self.client.get("/csrf-token/")
        token = token_response.json()["csrfToken"]
        response = self.client.post(
            "/csrf-check/", {"csrfmiddlewaretoken": token}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")
