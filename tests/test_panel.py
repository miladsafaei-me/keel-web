"""keel_web.panel and keel_web.newsletter: the staff panel's own pages, with the host's sidebar."""
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from keel_web.newsletter.models import NewsletterSubscriber, subscribe

PANEL = {
    "admin_shell": {
        "brand_name": "Test Site",
        "home_url": "keel_web_panel:dashboard",
        "logout_url": "keel_web_panel:logout",
        "profile_url": "keel_web_panel:password_change",
        "client_url": None,
        "nav": "tests.hostapp.panel_urls.nav",
        "dashboard_cards": ("tests.hostapp.panel_urls.cards",),
    },
}


@override_settings(ROOT_URLCONF="tests.hostapp.panel_urls", LOGIN_URL="keel_web_panel:login", KEEL_WEB=PANEL)
class PanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_superuser("owner", "owner@example.com", "pw")
        cls.staff = User.objects.create_user("helper", "helper@example.com", "pw", is_staff=True)

    def test_anonymous_goes_to_sign_in(self):
        response = self.client.get("/panel/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/panel/login/"))

    def test_sign_in_page_and_sign_in(self):
        page = self.client.get("/panel/login/")
        self.assertContains(page, "Sign in")
        self.assertContains(page, "noindex")
        response = self.client.post("/panel/login/", {"username": "owner", "password": "pw"})
        self.assertRedirects(response, "/panel/", fetch_redirect_response=False)

    def test_dashboard_has_the_hosts_sidebar_and_cards(self):
        self.client.force_login(self.owner)
        html = self.client.get("/panel/").content.decode()
        self.assertIn("Test Site", html)
        self.assertIn('href="/panel/newsletter/"', html)
        self.assertIn("Things", html)
        self.assertIn('action="/panel/logout/"', html)
        self.assertNotIn("Switch to client", html)

    def test_users_are_superuser_only(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/panel/users/").status_code, 302)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get("/panel/users/"), "helper")
        self.assertEqual(self.client.get(f"/panel/users/{self.staff.pk}/").status_code, 200)

    def test_owner_cannot_lock_themself_out(self):
        self.client.force_login(self.owner)
        response = self.client.post(f"/panel/users/{self.owner.pk}/", {
            "username": "owner", "email": "owner@example.com", "is_active": "on", "is_staff": "on"})
        self.assertContains(response, "cannot lock yourself out")
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.is_superuser)

    def test_add_user_and_set_password(self):
        self.client.force_login(self.owner)
        response = self.client.post("/panel/users/new/", {
            "username": "newbie", "password1": "a-long-Pass-123", "password2": "a-long-Pass-123", "is_staff": "on"})
        newbie = User.objects.get(username="newbie")
        self.assertRedirects(response, f"/panel/users/{newbie.pk}/", fetch_redirect_response=False)
        self.client.post(f"/panel/users/{newbie.pk}/password/", {"new_password1": "other-Pass-456", "new_password2": "other-Pass-456"})
        newbie.refresh_from_db()
        self.assertTrue(newbie.check_password("other-Pass-456"))

    def test_logout_is_post(self):
        self.client.force_login(self.owner)
        response = self.client.post("/panel/logout/")
        self.assertRedirects(response, "/panel/login/", fetch_redirect_response=False)


@override_settings(ROOT_URLCONF="tests.hostapp.panel_urls", LOGIN_URL="keel_web_panel:login", KEEL_WEB=PANEL)
class NewsletterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_superuser("owner", "owner@example.com", "pw")

    def setUp(self):
        self.client.force_login(self.owner)

    def test_subscribe_keeps_one_row_and_brings_back(self):
        row = subscribe("Ada@Example.com", source="home")
        row.unsubscribe()
        again = subscribe("ada@example.com")
        self.assertEqual(again.pk, row.pk)
        self.assertEqual(again.status, NewsletterSubscriber.Status.ACTIVE)
        self.assertEqual(again.source, "home")

    def test_list_add_toggle_export_delete(self):
        self.client.post("/panel/newsletter/", {"email": "b@example.com", "name": "B"})
        row = NewsletterSubscriber.objects.get(email="b@example.com")
        self.assertContains(self.client.get("/panel/newsletter/"), "b@example.com")
        self.client.post(f"/panel/newsletter/{row.pk}/toggle/")
        row.refresh_from_db()
        self.assertEqual(row.status, "unsubscribed")
        csv = self.client.get("/panel/newsletter/export.csv?status=unsubscribed").content.decode()
        self.assertIn("b@example.com", csv)
        self.client.post(f"/panel/newsletter/{row.pk}/delete/")
        self.assertFalse(NewsletterSubscriber.objects.exists())


JOIN = {"admin_shell": {**PANEL["admin_shell"], "signup": True, "logout_url": "keel_web_panel:logout"}}


@override_settings(ROOT_URLCONF="tests.hostapp.panel_urls", LOGIN_URL="join", KEEL_WEB=JOIN)
class JoinTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def signup(self, email="m@example.com", **extra):
        return self.client.post("/join", {"action": "up", "up-name": "Mina Rad", "up-email": email,
                                          "up-password1": "a-long-Pass-123", "up-password2": "a-long-Pass-123",
                                          "up-newsletter": "on", **extra})

    def test_page_has_both_forms_and_noindex(self):
        response = self.client.get("/join")
        self.assertContains(response, 'id="join-sign-in"')
        self.assertContains(response, 'id="join-sign-up"')
        self.assertEqual(response["X-Robots-Tag"], "noindex")

    @override_settings(KEEL_WEB=PANEL)
    def test_sign_up_is_off_by_default(self):
        self.assertNotContains(self.client.get("/join"), 'id="join-sign-up"')
        self.signup()
        self.assertFalse(User.objects.filter(email="m@example.com").exists())

    def test_sign_up_makes_a_member_on_the_newsletter(self):
        response = self.signup()
        self.assertRedirects(response, "/join", fetch_redirect_response=False)
        user = User.objects.get(email="m@example.com")
        self.assertFalse(user.is_staff)
        self.assertEqual(user.first_name, "Mina")
        self.assertTrue(NewsletterSubscriber.objects.filter(email="m@example.com", status="active").exists())
        page = self.client.get("/join")
        self.assertContains(page, "Your account")
        self.client.post("/join", {"action": "newsletter"})
        self.assertEqual(NewsletterSubscriber.objects.get(email="m@example.com").status, "unsubscribed")
        self.assertEqual(self.client.get("/panel/").status_code, 302)
        self.client.post("/join", {"action": "out"})
        self.assertNotContains(self.client.get("/join"), "Your account")

    def test_trap_and_duplicate_email(self):
        self.signup(**{"up-website": "spam"})
        self.assertFalse(User.objects.exists())
        self.signup()
        self.client.logout()
        self.assertContains(self.signup(), "already has an account")

    def test_staff_sign_in_goes_to_the_panel_and_next_is_kept(self):
        User.objects.create_user("boss", "boss@example.com", "pw", is_staff=True)
        response = self.client.post("/join", {"action": "in", "in-username": "boss", "in-password": "pw"})
        self.assertRedirects(response, "/panel/", fetch_redirect_response=False)
        self.client.logout()
        response = self.client.post("/join", {"action": "in", "in-username": "boss", "in-password": "pw",
                                              "next": "/panel/users/"})
        self.assertRedirects(response, "/panel/users/", fetch_redirect_response=False)
        response = self.client.post("/panel/logout/")
        self.assertRedirects(response, "/join", fetch_redirect_response=False)

    def test_sign_up_rate_limit(self):
        for i in range(5):
            self.signup(f"u{i}@example.com")
            self.client.logout()
        self.assertContains(self.signup("late@example.com"), "Too many new accounts")
