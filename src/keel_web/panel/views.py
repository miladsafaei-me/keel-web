"""The panel's own pages: sign in and out, the dashboard, your password, and the users.

Mount once under the panel's root with ``include("keel_web.panel.urls")`` and point
``LOGIN_URL`` at ``keel_web_panel:login``. The dashboard shows the cards and lists the
host names in ``KEEL_WEB["admin_shell"]["dashboard_cards"]`` and ``["dashboard_panels"]``.
"""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.module_loading import import_string
from django.views.decorators.http import require_POST

from keel_web.admin_shell.context import panel_url, render_panel, staff_required
from keel_web.config import admin_shell_setting

from .forms import (PanelLoginForm, PanelPasswordChangeForm, PanelSetPasswordForm, UserCreateForm, UserEditForm)


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
    next_page = reverse_lazy("keel_web_panel:login")


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
