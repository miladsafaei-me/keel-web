"""Tests for keel_web.frontend.bundles and {% css_bundle %}.

Run: DJANGO_SETTINGS_MODULE=tests.settings python -m django test tests.test_frontend_bundles
"""
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.template import Context, Template, TemplateSyntaxError
from django.test import SimpleTestCase, override_settings

from keel_web.frontend import bundles


class CssBundleTests(SimpleTestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.static = Path(tmp.name)
        for path, css in {
            "vendor/fonts/inter.css": "@font-face{src:url(inter.woff2)}",
            "css/base.css": "body{background:url(../img/ground.png)}",
            "css/pages/home.css": ".hero{background:url('/static/abs.png')}",
        }.items():
            (self.static / path).parent.mkdir(parents=True, exist_ok=True)
            (self.static / path).write_text(css)
        self.use({"site": ["vendor/fonts/inter.css", "css/base.css"], "home": ["css/pages/home.css"]})

    def use(self, declared, enabled=True):
        override = override_settings(
            STATICFILES_DIRS=[str(self.static)],
            KEEL_WEB={"frontend": {"enabled": enabled, "output_dir": str(self.static), "css_bundles": declared}},
        )
        override.enable()
        self.addCleanup(override.disable)

    def render(self, text):
        return Template("{% load keel_frontend %}" + text).render(Context())

    def test_relative_urls_are_rebased_onto_the_bundle_directory(self):
        css = bundles.render("site")
        self.assertIn("url('../vendor/fonts/inter.woff2')", css)
        self.assertIn("url('../img/ground.png')", css)

    def test_absolute_urls_are_left_as_written(self):
        self.assertIn("url('/static/abs.png')", bundles.render("home"))

    def test_an_unbuilt_bundle_links_each_source(self):
        html = self.render('{% css_bundle "site" %}')
        self.assertEqual(html.count("<link"), 2)
        self.assertIn('href="/static/vendor/fonts/inter.css"', html)

    def test_a_built_bundle_is_one_link(self):
        bundles.build_all()
        html = self.render('{% css_bundle "site" %}')
        self.assertEqual(html, '<link rel="stylesheet" href="/static/keel_frontend/site.css">')

    def test_a_disabled_frontend_links_sources_even_when_built(self):
        bundles.build_all()
        self.use({"site": ["vendor/fonts/inter.css", "css/base.css"]}, enabled=False)
        self.assertEqual(self.render('{% css_bundle "site" %}').count("<link"), 2)

    def test_an_unknown_bundle_is_a_template_error(self):
        with self.assertRaises(TemplateSyntaxError):
            self.render('{% css_bundle "nope" %}')

    def test_a_missing_source_is_named(self):
        self.use({"broken": ["css/gone.css"]})
        self.assertEqual(bundles.missing_sources(), ["broken: css/gone.css"])

    def test_the_command_builds_every_bundle_and_drops_undeclared_ones(self):
        stale = self.static / "keel_frontend" / "retired.css"
        stale.parent.mkdir(parents=True)
        stale.write_text("")
        call_command("build_frontend_assets", stdout=StringIO())
        self.assertTrue((self.static / "keel_frontend" / "site.css").is_file())
        self.assertTrue((self.static / "keel_frontend" / "home.css").is_file())
        self.assertFalse(stale.exists())
