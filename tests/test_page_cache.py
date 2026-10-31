"""Tests for keel_web.page_cache.

Run: DJANGO_SETTINGS_MODULE=tests.settings python -m django test tests.test_page_cache
"""
import gzip

from django.contrib.auth.models import User
from django.core.cache import caches
from django.http import HttpResponse, HttpResponseServerError
from django.middleware.csrf import get_token
from django.test import RequestFactory, TestCase, override_settings

from keel_web.page_cache import HEADER, cached_page, data_fingerprint

LOCMEM = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "keel-web-page-cache-tests",
    }
}


@override_settings(CACHES=LOCMEM)
class CachedPageTests(TestCase):
    def setUp(self):
        caches["default"].clear()
        self.request = RequestFactory().get("/")
        self.renders = 0

    def renderer(self, body="page", response_class=HttpResponse):
        def render():
            self.renders += 1
            return response_class(body)

        return render

    def serve(self, version="v1", slot="home", render=None, request=None):
        return cached_page(
            request or self.request,
            slot=slot,
            version=version,
            render=render or self.renderer(),
        )

    def test_first_request_renders_and_the_next_is_served_from_the_cache(self):
        first = self.serve()
        second = self.serve()
        self.assertEqual((first[HEADER], second[HEADER]), ("miss", "hit"))
        self.assertEqual(second.content, b"page")
        self.assertEqual(self.renders, 1)

    def test_a_new_version_renders_again_and_is_then_served(self):
        self.serve(render=self.renderer("old"))
        changed = self.serve(version="v2", render=self.renderer("new"))
        again = self.serve(version="v2", render=self.renderer("never"))
        self.assertEqual((changed[HEADER], changed.content), ("miss", b"new"))
        self.assertEqual((again[HEADER], again.content), ("hit", b"new"))
        self.assertEqual(self.renders, 2)

    def test_two_slots_never_share_an_entry(self):
        self.serve(slot="home:public", render=self.renderer("public"))
        staff = self.serve(slot="home:staff", render=self.renderer("staff"))
        self.assertEqual((staff[HEADER], staff.content), ("miss", b"staff"))

    def test_the_stored_content_type_is_kept(self):
        self.serve(render=lambda: HttpResponse("{}", content_type="application/json"))
        self.assertEqual(self.serve()["Content-Type"], "application/json")

    def test_the_previous_copy_is_served_while_another_request_renders(self):
        self.serve(render=self.renderer("old"))
        seen = {}

        def slow_render():
            # A second request arriving mid-render, as another worker's would.
            seen["response"] = self.serve(version="v2", render=self.renderer("never"))
            return HttpResponse("new")

        finished = self.serve(version="v2", render=slow_render)
        self.assertEqual((seen["response"][HEADER], seen["response"].content), ("stale", b"old"))
        self.assertEqual(finished.content, b"new")
        self.assertEqual(self.serve(version="v2")[HEADER], "hit")

    def test_the_lock_is_released_when_a_render_raises(self):
        self.serve(render=self.renderer("old"))

        def boom():
            raise RuntimeError("render failed")

        with self.assertRaises(RuntimeError):
            self.serve(version="v2", render=boom)
        # A held lock would answer "stale" here; a released one renders.
        self.assertEqual(self.serve(version="v2")[HEADER], "miss")

    def test_an_error_response_is_not_stored(self):
        self.serve(render=self.renderer("boom", HttpResponseServerError))
        self.assertEqual(self.serve()[HEADER], "miss")
        self.assertEqual(self.renders, 2)

    def test_a_private_response_is_not_stored(self):
        def private():
            response = HttpResponse("mine")
            response["Cache-Control"] = "private, max-age=0"
            return response

        self.serve(render=private)
        self.assertEqual(self.serve()[HEADER], "miss")

    def test_a_render_that_asked_for_a_csrf_token_is_not_stored(self):
        request = RequestFactory().get("/")

        def with_token():
            return HttpResponse(get_token(request))

        self.serve(render=with_token, request=request)
        self.assertEqual(self.serve()[HEADER], "miss")

    def test_a_gzip_accepting_client_gets_the_stored_compressed_copy(self):
        body = "<p>figure</p>" * 500
        self.serve(render=self.renderer(body))
        request = RequestFactory().get("/", HTTP_ACCEPT_ENCODING="gzip, deflate, br")
        response = self.serve(request=request)
        self.assertEqual(response["Content-Encoding"], "gzip")
        self.assertIn("Accept-Encoding", response["Vary"])
        self.assertEqual(gzip.decompress(response.content).decode(), body)

    def test_a_client_without_gzip_gets_the_plain_copy(self):
        self.serve(render=self.renderer("plain"))
        response = self.serve()
        self.assertFalse(response.has_header("Content-Encoding"))
        self.assertEqual(response.content, b"plain")


class DataFingerprintTests(TestCase):
    def test_is_stable_while_nothing_is_written(self):
        User.objects.create(username="steady")
        self.assertEqual(data_fingerprint(User), data_fingerprint(User))

    def test_changes_when_a_row_is_inserted_or_deleted(self):
        empty = data_fingerprint(User)
        user = User.objects.create(username="alice")
        inserted = data_fingerprint(User)
        user.delete()
        self.assertNotEqual(empty, inserted)
        self.assertNotEqual(inserted, data_fingerprint(User))

    def test_names_every_model_it_was_given(self):
        from django.contrib.auth.models import Group

        self.assertNotEqual(data_fingerprint(User), data_fingerprint(User, Group))


@override_settings(CACHES=LOCMEM)
class BackgroundRefreshTests(TestCase):
    def setUp(self):
        caches["default"].clear()
        self.request = RequestFactory().get("/")
        self.renders = []

    def serve(self, version, body, compatibility="static-a"):
        def render():
            self.renders.append(body)
            return HttpResponse(body)

        return cached_page(
            self.request,
            slot="home",
            version=version,
            render=render,
            background_refresh=True,
            compatibility=compatibility,
        )

    def test_a_stale_copy_is_served_at_once_and_refreshed_after_the_response_closes(self):
        self.serve("v1", "old")
        stale = self.serve("v2", "new")
        self.assertEqual((stale[HEADER], stale.content), ("stale", b"old"))
        self.assertEqual(self.renders, ["old"])
        stale.close()
        self.assertEqual(self.renders, ["old", "new"])
        fresh = self.serve("v2", "never")
        self.assertEqual((fresh[HEADER], fresh.content), ("hit", b"new"))

    def test_only_one_refresh_is_started_while_one_is_pending(self):
        self.serve("v1", "old")
        first = self.serve("v2", "new")
        second = self.serve("v2", "again")
        self.assertEqual(second[HEADER], "stale")
        second.close()
        first.close()
        self.assertEqual(self.renders, ["old", "new"])

    def test_a_copy_from_other_static_files_is_never_served_stale(self):
        self.serve("v1", "old", compatibility="static-a")
        changed = self.serve("v2", "new", compatibility="static-b")
        self.assertEqual((changed[HEADER], changed.content), ("miss", b"new"))

    def test_a_failed_refresh_keeps_the_stale_copy_and_frees_the_lock(self):
        self.serve("v1", "old")

        def broken():
            raise RuntimeError("render failed")

        stale = cached_page(self.request, slot="home", version="v2", render=broken,
                            background_refresh=True, compatibility="static-a")
        with self.assertLogs("keel_web.page_cache", level="ERROR"):
            stale.close()
        retry = self.serve("v2", "new")
        self.assertEqual((retry[HEADER], retry.content), ("stale", b"old"))
        retry.close()
        self.assertEqual(self.serve("v2", "never").content, b"new")
