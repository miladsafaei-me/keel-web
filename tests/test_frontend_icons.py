"""Tests for keel_web.frontend.icons (the stylesheet half; font subsetting needs real fonts).

Run: DJANGO_SETTINGS_MODULE=tests.settings python -m django test tests.test_frontend_icons
"""
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from keel_web.frontend import icons

STOCK = (
    '.fa{font-family:var(--fa-style-family,"Font Awesome 6 Free")}'
    ".fa,.fa-brands,.fa-solid,.fab,.fas{display:inline-block}"
    ".fa-2x{font-size:2em}.fa-spin{animation-name:fa-spin}"
    '.fa-arrow-down:before{content:"\\f063"}.fa-close:before,.fa-xmark:before{content:"\\f00d"}'
    '.fa-bolt:before{content:"\\f0e7"}'
    "@media (prefers-reduced-motion:reduce){.fa-spin{animation-delay:-1ms}}"
    "@keyframes fa-spin{0%{transform:rotate(0)}to{transform:rotate(1turn)}}"
    ':host,:root{--fa-font-solid:normal 900 1em/1 "Font Awesome 6 Free"}'
    '@font-face{font-family:"Font Awesome 6 Free";font-weight:900;font-display:block;'
    'src:url(../webfonts/fa-solid-900.woff2) format("woff2"),url(../webfonts/fa-solid-900.ttf) format("truetype")}'
    '@font-face{font-family:"Font Awesome 6 Brands";font-display:block;src:url(../webfonts/fa-brands-400.woff2) format("woff2")}'
    '@font-face{font-family:"FontAwesome";font-display:block;src:url(../webfonts/fa-solid-900.woff2) format("woff2")}'
    ".fa-solid,.fas{font-weight:900}"
)
USED = {"fa-solid", "fa-arrow-down", "fa-xmark"}
FAMILIES = {"fa-solid-900": "fa-solid-900.subset.woff2"}


class IconSubsetStylesheetTests(SimpleTestCase):
    def setUp(self):
        self.css = icons.prune_css(STOCK, USED, FAMILIES)

    def test_codepoints_are_read_for_every_alias(self):
        self.assertEqual(
            icons.icon_codepoints(STOCK),
            {"fa-arrow-down": 0xF063, "fa-close": 0xF00D, "fa-xmark": 0xF00D, "fa-bolt": 0xF0E7},
        )

    def test_used_icons_stay_and_unused_ones_go(self):
        self.assertIn('.fa-arrow-down:before{content:"\\f063"}', self.css)
        self.assertIn('.fa-xmark:before{content:"\\f00d"}', self.css)
        for gone in ("fa-close", "fa-bolt", "fa-2x", "fa-spin", "@media"):
            self.assertNotIn(gone, self.css)

    def test_the_rules_every_icon_needs_stay(self):
        self.assertIn(".fa,.fa-brands,.fa-solid,.fab,.fas{display:inline-block}", self.css)
        self.assertIn(":host,:root{", self.css)

    def test_only_used_families_keep_a_face_pointed_at_the_subset_with_swap(self):
        self.assertIn('src:url(fa-solid-900.subset.woff2) format("woff2")', self.css)
        self.assertIn("font-display:swap", self.css)
        self.assertNotIn("Font Awesome 6 Brands", self.css)
        self.assertNotIn('"FontAwesome"', self.css)
        self.assertNotIn("font-display:block", self.css)

    def test_tokens_are_scanned_from_source_and_skipped_directories_are_not(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "page.html").write_text('<i class="fa-solid fa-bolt"></i>')
            Path(root, "nav.py").write_text('ICON = "fa-circle-check"')
            Path(root, "node_modules").mkdir()
            Path(root, "node_modules", "lib.js").write_text("fa-ghost")
            self.assertEqual(icons.scan_tokens([root]), {"fa-solid", "fa-bolt", "fa-circle-check"})
