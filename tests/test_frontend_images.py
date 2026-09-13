"""Tests for keel_web.frontend.images and {% media_img %}.

Run: DJANGO_SETTINGS_MODULE=tests.settings python -m django test tests.test_frontend_images
"""
import os
import tempfile
from pathlib import Path

from django.template import Context, Template
from django.test import SimpleTestCase, override_settings
from PIL import Image

from keel_web.frontend import images


class MediaImageTests(SimpleTestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.logo = self.root / "logos" / "brand.png"
        self.logo.parent.mkdir()
        Image.new("RGBA", (512, 512), (200, 30, 30, 255)).save(self.logo)
        override = override_settings(MEDIA_ROOT=str(self.root), MEDIA_URL="/media/")
        override.enable()
        self.addCleanup(override.disable)

    def file_for(self, url):
        return self.root / url.removeprefix("/media/")

    def test_a_media_image_gets_webp_at_one_and_two_times_its_box(self):
        attrs = images.img_attrs("/media/logos/brand.png", 48, 48)
        self.assertTrue(attrs["src"].endswith(".48w.webp"))
        one, two = [part.split()[0] for part in attrs["srcset"].split(", ")]
        self.assertTrue(two.endswith(".96w.webp"))
        with Image.open(self.file_for(one)) as small, Image.open(self.file_for(two)) as large:
            self.assertEqual((small.size, large.size), ((48, 48), (96, 96)))

    def test_a_small_source_is_never_upscaled(self):
        Image.new("RGB", (64, 64)).save(self.logo)
        attrs = images.img_attrs("/media/logos/brand.png", 48, 48)
        with Image.open(self.file_for(attrs["srcset"].split(", ")[1].split()[0])) as image:
            self.assertEqual(image.size, (64, 64))

    def test_replacing_the_source_gives_the_variant_a_new_name(self):
        first = images.variant_url("/media/logos/brand.png", 48)
        Image.new("RGB", (300, 300)).save(self.logo)
        os.utime(self.logo, ns=(1, 1))
        self.assertNotEqual(first, images.variant_url("/media/logos/brand.png", 48))

    def test_anything_that_is_not_a_media_raster_passes_through(self):
        for url in ("/static/logo.png", "https://example.com/a.png", "/media/logos/gone.png",
                    "/media/../outside.png", "/media/logos/mark.svg"):
            with self.subTest(url=url):
                self.assertEqual(images.img_attrs(url, 48, 48), {"src": url, "width": 48, "height": 48})

    def test_the_tag_writes_the_box_and_the_attributes_it_was_given(self):
        html = Template(
            '{% load keel_frontend %}{% media_img url 48 48 class="logo" alt="" loading="lazy" data_f="logo" hidden=hide %}'
        ).render(Context({"url": "/media/logos/brand.png", "hide": False}))
        self.assertTrue(html.startswith('<img class="logo" src="/media/logos/_v/brand.'))
        for part in ('srcset="', 'width="48"', 'height="48"', 'alt=""', 'loading="lazy"', 'data-f="logo"'):
            self.assertIn(part, html)
        self.assertNotIn(" hidden", html)

    def test_a_variant_is_cached_for_a_year_and_a_source_is_not(self):
        default = "public, max-age=60"
        self.assertIn("immutable", images.cache_control_for("logos/_v/brand.abc.48w.webp", default))
        self.assertEqual(images.cache_control_for("logos/brand.png", default), default)
