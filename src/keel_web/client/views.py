"""Client-panel shell views.

Only the domain-neutral views are here: the auth-gated base, the account-settings
page (profile / email / password / avatar + persona builder), a billing stub, and
the email-verification resend action. Every trading / monetization page in the
SignalBots panel (signals consoles, my-products, partner/affiliate, onboarding)
stays in the host — those read product services and are Bucket-0.

``ClientBaseView`` carries no product coupling: the sidebar nav comes from
``KEEL_WEB["client_nav"]`` and any panel-wide extras (e.g. an activation banner)
from the optional ``KEEL_WEB["client_base_context_hook"]``.
"""
from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, View

from ..auth.forms import (
    AvatarForm,
    EmailChangeForm,
    PasswordChangeForm,
    ProfileForm,
)
from ..auth.personas import (
    PERSONA_CHOICES,
    PERSONA_LAYER_ORDER,
    PERSONA_PRESETS,
)
from ..config import call_hook, web_setting
from .navigation import resolve_client_nav


class ClientBaseView(LoginRequiredMixin, TemplateView):
    redirect_field_name = "next"

    page_title: str = ""
    page_pretitle: str = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["client_nav"] = resolve_client_nav()
        ctx["page_title"] = self.page_title
        ctx["page_pretitle"] = self.page_pretitle
        # The host injects any panel-wide extras (activation banner, support-bot
        # URL, etc.) so the base view stays product-neutral.
        extra = call_hook(web_setting("client_base_context_hook"), self.request, default=None)
        if isinstance(extra, dict):
            ctx.update(extra)
        return ctx


class ProfileView(ClientBaseView):
    template_name = "keel_web_client/profile.html"
    page_title = "Profile"
    page_pretitle = "Settings"

    FORM_KEYS = ("profile", "email", "password", "avatar")

    def _build_forms(self, *, bound: str | None, request):
        user = request.user
        return {
            "profile": ProfileForm(
                request.POST if bound == "profile" else None,
                instance=user,
            ),
            "email": EmailChangeForm(
                user,
                request.POST if bound == "email" else None,
            ),
            "password": PasswordChangeForm(
                user,
                request.POST if bound == "password" else None,
            ),
            "avatar": AvatarForm(
                user,
                request.POST if bound == "avatar" else None,
                request.FILES if bound == "avatar" else None,
            ),
        }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        forms = kwargs.get("forms") or self._build_forms(bound=None, request=self.request)
        ctx["profile_form"] = forms["profile"]
        ctx["email_form"] = forms["email"]
        ctx["password_form"] = forms["password"]
        ctx["avatar_form"] = forms["avatar"]
        ctx["active_section"] = kwargs.get("active_section", "profile")
        ctx["persona_presets"] = PERSONA_PRESETS
        ctx["persona_choices_json"] = json.dumps(PERSONA_CHOICES)
        ctx["persona_layer_order"] = PERSONA_LAYER_ORDER
        ctx["persona_layer_order_json"] = json.dumps(list(PERSONA_LAYER_ORDER))
        ctx["persona_current_json"] = json.dumps(self.request.user.avatar_config or {})
        avatar_url = ""
        if self.request.user.avatar:
            try:
                avatar_url = self.request.user.avatar.url
            except ValueError:
                avatar_url = ""
        ctx["persona_avatar_url_json"] = json.dumps(avatar_url)
        from ..auth.phone_helpers import country_data
        ctx["phone_countries"] = country_data()
        return ctx

    def post(self, request, *args, **kwargs):
        action = request.POST.get("form")
        if action not in self.FORM_KEYS:
            return redirect(reverse("client:profile"))

        forms = self._build_forms(bound=action, request=request)
        bound_form = forms[action]

        if not bound_form.is_valid():
            messages.error(request, "Please correct the errors below.")
            ctx = self.get_context_data(forms=forms, active_section=action)
            return self.render_to_response(ctx)

        if action == "profile":
            bound_form.save()
            messages.success(request, "Profile updated.")
        elif action == "email":
            bound_form.save()
            messages.success(request, "Email address updated.")
        elif action == "password":
            bound_form.save()
            update_session_auth_hash(request, bound_form.user)
            messages.success(request, "Password updated.")
        elif action == "avatar":
            bound_form.save()
            messages.success(request, "Avatar updated.")

        if action == "avatar":
            return redirect(reverse("client:profile"))
        return redirect(f"{reverse('client:profile')}#section-{action}")


class BillingView(ClientBaseView):
    template_name = "keel_web_client/billing.html"
    page_title = "Billing"
    page_pretitle = "Settings"


class ResendVerificationView(LoginRequiredMixin, View):
    """Re-send the email-verification link for the current user (POST only).

    Backs the "Resend" action on the unverified-email banner. Delegates to
    allauth, which handles the per-address cooldown and primary-email lookup.
    """

    def post(self, request, *args, **kwargs):
        from allauth.account.models import EmailAddress

        user = request.user
        address = (
            EmailAddress.objects.filter(user=user, verified=False)
            .order_by("-primary")
            .first()
        )
        if address is None and user.email and not user.emailaddress_set.exists():
            # Defensive: no EmailAddress row at all yet. Create the primary one
            # so allauth can confirm it (rare — allauth seeds it at signup).
            address, _ = EmailAddress.objects.get_or_create(
                user=user, email=user.email.lower(), defaults={"primary": True}
            )

        if address is not None:
            address.send_confirmation(request)
            messages.success(
                request,
                "Verification email sent. Check your inbox (and spam folder).",
            )
        else:
            messages.info(request, "Your email address is already verified.")
        return redirect(request.META.get("HTTP_REFERER") or reverse("client:profile"))
