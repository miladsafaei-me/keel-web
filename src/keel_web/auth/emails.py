"""Transactional email helpers.

``brand_email_context()`` supplies the chrome (logo, brand name, home link)
expected by a base email template so every outbound email shares one design.
``send_transactional_email()`` is the reusable entry point for non-allauth
emails; allauth's own emails get the same chrome injected via
``keel_web.auth.adapters.AccountAdapter.send_mail``.

Branding is read from standard settings (``BRAND_NAME``, ``SITE_BASE_URL``,
``DEFAULT_FROM_EMAIL``) plus ``KEEL_WEB["email_logo_static"]`` for the logo path.
"""
from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.templatetags.static import static
from django.template.loader import render_to_string

from ..config import web_setting


def brand_email_context() -> dict:
    """Branding values shared by every transactional email template."""
    base_url = getattr(settings, "SITE_BASE_URL", "").rstrip("/")
    return {
        "brand_name": getattr(settings, "BRAND_NAME", "") or "",
        "site_base_url": base_url,
        # Absolute URL is required: email clients have no page origin to resolve
        # a root-relative {% static %} path against.
        "logo_url": f"{base_url}{static(web_setting('email_logo_static'))}",
    }


def send_transactional_email(
    *,
    subject: str,
    to: str | list[str],
    template: str,
    context: dict | None = None,
    text_template: str | None = None,
) -> int:
    """Render and send a branded transactional email.

    ``template`` is an HTML template extending the host's base email template.
    ``text_template`` is an optional plain-text alternative; when omitted, a
    minimal text part is derived so the message is never HTML-only.
    """
    recipients = [to] if isinstance(to, str) else list(to)
    ctx = {**brand_email_context(), **(context or {})}

    html_body = render_to_string(template, ctx)
    if text_template:
        text_body = render_to_string(text_template, ctx)
    else:
        text_body = ctx.get("preheader") or subject

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    message.attach_alternative(html_body, "text/html")
    return message.send()
