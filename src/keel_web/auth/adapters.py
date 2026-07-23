"""allauth adapters: username-from-email generation, branded mail, gated lead hook.

The only host-domain coupling — recording a Lead when a signup arrives through a
product gate — is neutralized into ``KEEL_WEB["signup_lead_hook"]``. The default
is no hook, so keel-web imports nothing domain-specific here.
"""
import logging
import smtplib

from django.utils.text import slugify
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from ..config import call_hook, web_setting

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    """Generate username from email when not provided."""

    def send_mail(self, template_prefix, email, context):
        # Inject shared brand chrome (logo, brand name, home link) so every
        # allauth email — verification, password reset — renders with the same
        # base email design as our own transactional emails.
        from .emails import brand_email_context

        context = {**brand_email_context(), **context}
        # A mail-delivery failure must never surface as a 500 to the user. The
        # verification email is sent inline during signup/login *after* the
        # account row is created, so an undeliverable address (e.g. the mail
        # server rejecting an unknown mailbox with SMTP 550) would otherwise
        # crash the request with the account half-created. Swallow transport
        # errors here and log them; verification is "optional" so the user can
        # still use the account and request a fresh email later.
        try:
            return super().send_mail(template_prefix, email, context)
        except (OSError, smtplib.SMTPException) as exc:
            logger.warning(
                "allauth send_mail failed for %s (%s): %s",
                email, template_prefix, exc,
            )
            return None

    def save_user(self, request, user, form, commit=True):
        if not user.username:
            base = user.email.split("@")[0] if user.email else "user"
            user.username = slugify(base)[:150] or "user"
            # Ensure uniqueness
            from django.contrib.auth import get_user_model
            User = get_user_model()
            orig = user.username
            n = 0
            while User.objects.filter(username=user.username).exists():
                n += 1
                user.username = f"{orig}{n}"[:150]
        saved = super().save_user(request, user, form, commit=commit)
        # If this signup came in through a product gate (a landing's "create a
        # free account" link carrying ``?src=<product-key>``), hand it to the
        # host's lead hook so support can follow up. Best-effort: a hook-side
        # failure must never break the signup itself (call_hook swallows errors).
        if commit and request is not None:
            src = (request.POST.get("signup_src") or "").strip().lower()
            if src:
                call_hook(
                    web_setting("signup_lead_hook"),
                    user=user,
                    product_key=src,
                    request=request,
                )
        return saved


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Generate username for social signups."""

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        if not user.username:
            email = data.get("email") or ""
            name = data.get("name") or ""
            base = email.split("@")[0] if email else (slugify(name or "user")[:30] or "user")
            user.username = slugify(base)[:150] or "user"
            from django.contrib.auth import get_user_model
            User = get_user_model()
            orig = user.username
            n = 0
            while User.objects.filter(username=user.username).exists():
                n += 1
                user.username = f"{orig}{n}"[:150]
        return user
