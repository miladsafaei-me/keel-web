"""Build the Font Awesome subset and the CSS bundles declared in ``KEEL_WEB["frontend"]``.

Run it before ``collectstatic``, where the hashed names are made: in an image build, a
deploy step or a local build that wants production assets. The icon subset is written
first because a bundle may include it.
"""

from pathlib import Path

from django.contrib.staticfiles import finders
from django.core.management.base import BaseCommand, CommandError

from keel_web.config import frontend_setting
from keel_web.frontend import bundles, icons


class Command(BaseCommand):
    help = "Build the Font Awesome subset and the CSS bundles declared in KEEL_WEB['frontend']."

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true", help="Verify every declared source resolves; write nothing.")

    def handle(self, *args, **options):
        missing = bundles.missing_sources()
        conf = frontend_setting("icons")
        stock = conf.get("css")
        if stock and not finders.find(stock):
            missing.append(f"icons: {stock}")
        if missing:
            raise CommandError("front-end sources not found:\n  " + "\n  ".join(missing))
        if options["check"]:
            self.stdout.write(self.style.SUCCESS(f"{len(bundles.declared())} bundles resolve."))
            return

        root = bundles.output_root()
        if root is None:
            raise CommandError("KEEL_WEB['frontend']['output_dir'] is not set.")

        if stock:
            tokens = icons.scan_tokens(conf.get("scan_roots") or (), conf.get("skip_dirs") or icons.DEFAULT_SKIP)
            report = icons.build(Path(finders.find(stock)), root / frontend_setting("bundle_dir"), tokens)
            fonts = ", ".join(f"{stem} {glyphs} glyphs {size // 1024 or 1} KB" for stem, (glyphs, size) in report["fonts"].items())
            self.stdout.write(f"icons: {report['icons']} used, stylesheet {report['css_bytes'] // 1024} KB, {fonts}")

        for name, size in bundles.build_all():
            self.stdout.write(f"bundle {name}: {size // 1024} KB")
        self.stdout.write(self.style.SUCCESS("front-end assets built."))
