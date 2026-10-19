"""keel_web.admin_theme: every stock admin page renders in the theme, with no Django stylesheet."""
import re
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.core.checks import run_checks
from django.test import TestCase, override_settings

import keel_web.admin_theme as admin_theme

CSS = Path(admin_theme.__file__).parent / "static" / "keel_web_admin_theme" / "css" / "admin-theme.css"
DJANGO_CSS = re.compile(r'admin/css/(base|forms|widgets|changelists|dashboard|login|nav_sidebar|responsive|dark_mode)\.css')


class AdminThemePagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("owner", "owner@example.com", "pw", first_name="Ada", last_name="Lovelace")
        cls.group = Group.objects.create(name="Editors")

    def setUp(self):
        self.client.force_login(self.user)

    def get_themed(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        html = response.content.decode()
        self.assertIn("keel_web_admin_theme/css/admin-theme.css", html, url)
        self.assertIsNone(DJANGO_CSS.search(html), url)
        return html

    def test_every_page_renders_in_the_theme(self):
        urls = [
            "/staff-admin/",
            "/staff-admin/auth/",
            "/staff-admin/auth/group/",
            "/staff-admin/auth/group/add/",
            f"/staff-admin/auth/group/{self.group.pk}/change/",
            f"/staff-admin/auth/group/{self.group.pk}/delete/",
            f"/staff-admin/auth/group/{self.group.pk}/history/",
            "/staff-admin/auth/user/",
            "/staff-admin/auth/user/?q=owner",
            "/staff-admin/auth/user/add/",
            f"/staff-admin/auth/user/{self.user.pk}/change/",
            f"/staff-admin/auth/user/{self.user.pk}/password/",
            "/staff-admin/password_change/",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.get_themed(url)

    def test_sidebar_lists_the_apps_and_marks_the_current_model(self):
        html = self.get_themed("/staff-admin/auth/group/")
        self.assertIn('class="kat-sidebar"', html)
        self.assertRegex(html, r'kat-nav-item is-active" href="/staff-admin/auth/group/"')
        self.assertIn(">Ada Lovelace<", html)

    def test_filters_open_in_a_drawer_and_bulk_delete_confirms(self):
        html = self.get_themed("/staff-admin/auth/user/")
        self.assertIn('id="changelist-filter"', html)
        self.assertIn("data-kat-drawer-open", html)
        response = self.client.post("/staff-admin/auth/group/", {"action": "delete_selected", "_selected_action": [self.group.pk]})
        self.assertContains(response, "kat-confirm")

    def test_signed_out_pages_use_the_auth_layout(self):
        self.client.logout()
        html = self.get_themed("/staff-admin/login/")
        self.assertIn('class="kat-auth"', html)
        self.assertNotIn('class="kat-sidebar"', html)

    @override_settings(KEEL_WEB={"admin_theme": {"brand_name": "Acme", "tagline": "Back office",
                                                 "model_icons": {"auth.group": "tag"}}})
    def test_host_settings_reach_the_chrome(self):
        html = self.get_themed("/staff-admin/")
        self.assertIn("Acme", html)
        self.assertIn("Back office", html)

    def test_boolean_icons_are_replaced(self):
        from django.contrib.staticfiles import finders

        found = finders.find("admin/img/icon-yes.svg")
        self.assertIn("admin_theme", found)

    def test_system_check_wants_the_theme_before_admin(self):
        with override_settings(INSTALLED_APPS=["django.contrib.admin", "keel_web.admin_theme"]):
            from keel_web.admin_theme.checks import check_theme_precedes_admin

            ids = [message.id for message in check_theme_precedes_admin()]
        self.assertEqual(ids, ["keel_web_admin_theme.E001"])
        self.assertEqual([m for m in run_checks() if m.id.startswith("keel_web_admin_theme")], [])


class AdminThemeStylesheetTests(TestCase):
    def test_raw_values_live_only_in_root_blocks(self):
        css = re.sub(r"/\*.*?\*/", "", CSS.read_text(), flags=re.S)
        css = re.sub(r":root(\[[^\]]*\])?\s*\{[^}]*\}", "", css)
        css = re.sub(r"@media[^{]*\{", "", css)
        for pattern in (r"#[0-9a-fA-F]{3,8}\b", r"\brgba?\(", r"(?<![\w-])\d+(\.\d+)?px\b", r"!important"):
            self.assertIsNone(re.search(pattern, css), pattern)
