"""Tests for keel_web.storage.KeelManifestStaticFilesStorage.

Run: DJANGO_SETTINGS_MODULE=tests.settings python -m django test tests.test_storage
"""
import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from keel_web.storage import KeelManifestStaticFilesStorage


class MissingFileFallbackTests(SimpleTestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)

    def storage(self):
        return KeelManifestStaticFilesStorage(location=self.root.name, base_url="/static/")

    def test_a_file_that_was_never_collected_gets_its_plain_url(self):
        self.assertEqual(self.storage().url("vendor/gone.css"), "/static/vendor/gone.css")

    def test_a_collected_file_still_gets_its_hashed_url(self):
        Path(self.root.name, "site.css").write_text("body{}")
        manifest = {"version": "1.1", "paths": {"site.css": "site.0123456789ab.css"}}
        Path(self.root.name, "staticfiles.json").write_text(json.dumps(manifest))
        self.assertEqual(self.storage().url("site.css"), "/static/site.0123456789ab.css")
