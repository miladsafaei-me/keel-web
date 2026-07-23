"""Staff-panel access mixins.

The Content-Editor group name and the "denied but authenticated" redirect target
are config seams (``KEEL_WEB["content_editor_group"]`` and
``["permission_denied_redirect"]``) so the mixins carry no project-specific
strings.
"""
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from ..config import web_setting


def content_editor_group() -> str:
    return web_setting("content_editor_group")


def is_content_editor(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.is_staff:
        return False
    return user.groups.filter(name=content_editor_group()).exists()


def is_superuser_only(user) -> bool:
    return user.is_authenticated and user.is_superuser


class _AdminPermissionDenied:
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect(web_setting("permission_denied_redirect"))
        return redirect_to_login(self.request.get_full_path(), login_url=settings.LOGIN_URL)


class StaffRequiredMixin(_AdminPermissionDenied, UserPassesTestMixin):
    """Allow only Django staff users."""

    def test_func(self):
        return self.request.user.is_staff


class AdminShellMixin(LoginRequiredMixin, StaffRequiredMixin):
    login_url = settings.LOGIN_URL


class ContentEditorAccessMixin(_AdminPermissionDenied, LoginRequiredMixin, UserPassesTestMixin):
    """Content views: superusers and Content-Editor group members may access."""

    login_url = settings.LOGIN_URL

    def test_func(self):
        return is_content_editor(self.request.user)


class SuperuserOnlyMixin(_AdminPermissionDenied, LoginRequiredMixin, UserPassesTestMixin):
    """Restricts a view to superusers only (Content Editors are blocked)."""

    login_url = settings.LOGIN_URL

    def test_func(self):
        return is_superuser_only(self.request.user)
