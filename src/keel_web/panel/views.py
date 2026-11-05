"""The panel's own pages: sign in and out, the dashboard, your password, and the users.

Mount once under the panel's root with ``include("keel_web.panel.urls")`` and point
``LOGIN_URL`` at ``keel_web_panel:login``. The dashboard shows the cards and lists the
host names in ``KEEL_WEB["admin_shell"]["dashboard_cards"]`` and ``["dashboard_panels"]``.
"""
from __future__ import annotations

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.module_loading import import_string
from django.views.decorators.http import require_POST

from keel_web.admin_shell.context import panel_url, render_panel, staff_required
from keel_web.config import admin_shell_setting

from .forms import (PanelLoginForm, PanelPasswordChangeForm, PanelSetPasswordForm, SignupForm, UserCreateForm,
                    UserEditForm)


class LoginView(auth_views.LoginView):
    template_name = "keel_web_panel/login.html"
    form_class = PanelLoginForm
    redirect_authenticated_user = False

    def get_default_redirect_url(self):
        return panel_url("home_url") or "/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"brand_name": admin_shell_setting("brand_name"), "login_title": admin_shell_setting("login_title"),
                    "login_text": admin_shell_setting("login_text"), "logo": admin_shell_setting("logo"),
                    "logo_round": admin_shell_setting("logo_round")})
        return ctx


class LogoutView(auth_views.LogoutView):
    """Sign out (POST), then back to the sign-in page the host names in ``LOGIN_URL``."""

    def get_default_redirect_url(self):
        return resolve_url(settings.LOGIN_URL)


def _hook_results(key, request) -> list:
    rows = []
    for dotted in admin_shell_setting(key):
        result = import_string(dotted)(request)
        rows.extend(result if isinstance(result, (list, tuple)) else [result])
    return rows


@staff_required
def dashboard(request):
    return render_panel(request, "keel_web_panel/dashboard.html", {
        "page_title": "Dashboard", "cards": _hook_results("dashboard_cards", request),
        "panels": _hook_results("dashboard_panels", request)})


@staff_required
def password_change(request):
    form = PanelPasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Your password is changed.")
        return redirect("keel_web_panel:password_change")
    return render_panel(request, "keel_web_panel/password.html", {
        "page_title": "Your password", "form": form, "subject": request.user})


def _superuser(view):
    @staff_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "Only a superuser can manage users.")
            return redirect(panel_url("home_url") or "/")
        return view(request, *args, **kwargs)

    wrapped.__name__ = view.__name__
    return wrapped


@_superuser
def user_list(request):
    users = get_user_model().objects.order_by("-is_superuser", "-is_staff", "username")
    q = request.GET.get("q", "").strip()
    if q:
        users = users.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q)
                             | Q(last_name__icontains=q))
    role = request.GET.get("role", "")
    if role == "staff":
        users = users.filter(is_staff=True)
    elif role == "inactive":
        users = users.filter(is_active=False)
    page = Paginator(users, 50).get_page(request.GET.get("page"))
    query = "&".join(f"{k}={v}" for k, v in (("q", q), ("role", role)) if v)
    return render_panel(request, "keel_web_panel/user_list.html", {
        "page_title": "Users", "page_pretitle": "Accounts", "page_obj": page, "q": q, "role": role, "query": query})


@_superuser
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"{user.get_username()} is added.")
        return redirect("keel_web_panel:user_edit", user.pk)
    return render_panel(request, "keel_web_panel/user_form.html", {
        "page_title": "Add a user", "page_pretitle": "Accounts", "form": form})


@_superuser
def user_edit(request, pk):
    subject = get_object_or_404(get_user_model(), pk=pk)
    form = UserEditForm(request.POST or None, instance=subject, editor=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{subject.get_username()} is saved.")
        return redirect("keel_web_panel:user_edit", subject.pk)
    return render_panel(request, "keel_web_panel/user_form.html", {
        "page_title": subject.get_username(), "page_pretitle": "Accounts", "form": form, "subject": subject})


@_superuser
def user_password(request, pk):
    subject = get_object_or_404(get_user_model(), pk=pk)
    form = PanelSetPasswordForm(subject, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        if subject.pk == request.user.pk:
            update_session_auth_hash(request, subject)
        messages.success(request, f"The password of {subject.get_username()} is changed.")
        return redirect("keel_web_panel:user_edit", subject.pk)
    return render_panel(request, "keel_web_panel/password.html", {
        "page_title": f"Password of {subject.get_username()}", "page_pretitle": "Accounts", "form": form,
        "subject": subject})


@_superuser
@require_POST
def user_delete(request, pk):
    subject = get_object_or_404(get_user_model(), pk=pk)
    if subject.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account.")
        return redirect("keel_web_panel:user_edit", subject.pk)
    name = subject.get_username()
    subject.delete()
    messages.success(request, f"{name} is deleted.")
    return redirect("keel_web_panel:user_list")


def _newsletter_on() -> bool:
    return apps.is_installed("keel_web.newsletter")


def _next_url(request, user) -> str:
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure()):
        return target
    return (panel_url("home_url") or "/") if user.is_staff else request.path


def _signup_allowed(request) -> bool:
    """At most ``signup_per_hour`` new accounts an hour from one address."""
    ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR", "")
    key = f"keel_web_signup:{ip}"
    count = cache.get(key, 0)
    if count >= admin_shell_setting("signup_per_hour"):
        return False
    cache.set(key, count + 1, 3600)
    return True


def join(request):
    """One page to sign in or create an account. Staff go on to the panel; a member signed in sees their
    account here (name, newsletter, sign out). Sign-up is open only when ``admin_shell["signup"]`` is True."""
    signup_on = admin_shell_setting("signup")
    login_form = PanelLoginForm(request, prefix="in")
    signup_form = SignupForm(prefix="up", newsletter=_newsletter_on()) if signup_on else None
    tab = "in"
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "in":
            login_form = PanelLoginForm(request, data=request.POST, prefix="in")
            if login_form.is_valid():
                login(request, login_form.get_user())
                return redirect(_next_url(request, login_form.get_user()))
        elif action == "up" and signup_on:
            tab = "up"
            signup_form = SignupForm(request.POST, prefix="up", newsletter=_newsletter_on())
            if request.POST.get("up-website"):
                return redirect(request.path)
            if signup_form.is_valid():
                if not _signup_allowed(request):
                    signup_form.add_error(None, "Too many new accounts from here. Try again in an hour.")
                else:
                    user = signup_form.save()
                    if signup_form.cleaned_data.get("newsletter"):
                        from keel_web.newsletter.models import subscribe

                        subscribe(user.email, name=user.get_full_name(), source="join")
                    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                    messages.success(request, "Your account is ready.")
                    return redirect(_next_url(request, user))
        elif action == "out":
            logout(request)
            return redirect(request.path)
        elif action == "newsletter" and request.user.is_authenticated and _newsletter_on():
            from keel_web.newsletter.models import NewsletterSubscriber, subscribe

            row = NewsletterSubscriber.objects.filter(email__iexact=request.user.email).first()
            if row and row.status == NewsletterSubscriber.Status.ACTIVE:
                row.unsubscribe()
                messages.success(request, "You will get no more newsletters.")
            elif request.user.email:
                subscribe(request.user.email, name=request.user.get_full_name(), source="join")
                messages.success(request, "You are on the newsletter.")
            return redirect(request.path)
    subscribed = False
    if request.user.is_authenticated and _newsletter_on() and request.user.email:
        from keel_web.newsletter.models import NewsletterSubscriber

        subscribed = NewsletterSubscriber.objects.filter(
            email__iexact=request.user.email, status=NewsletterSubscriber.Status.ACTIVE).exists()
    response = render(request, "keel_web_panel/join.html", {
        "login_form": login_form, "signup_form": signup_form, "tab": tab, "next": request.GET.get("next", ""),
        "brand_name": admin_shell_setting("brand_name"), "join_title": admin_shell_setting("join_title"),
        "join_text": admin_shell_setting("join_text"), "logo": admin_shell_setting("logo"),
        "logo_round": admin_shell_setting("logo_round"), "newsletter_on": _newsletter_on(), "subscribed": subscribed,
        "panel_home": panel_url("home_url"), "logout_url": panel_url("logout_url"), "site_url": panel_url("site_url")})
    response["X-Robots-Tag"] = "noindex"
    return response
