from __future__ import annotations

import secrets

from django.db import models
from django.utils import timezone


def _token() -> str:
    return secrets.token_urlsafe(24)


class NewsletterSubscriber(models.Model):
    """One email on the list. Unsubscribing keeps the row, so the address is never mailed again by mistake."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Subscribed"
        UNSUBSCRIBED = "unsubscribed", "Unsubscribed"

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120, blank=True)
    language = models.CharField(max_length=12, blank=True, help_text="The language they signed up in.")
    source = models.CharField(max_length=120, blank=True, help_text="Where they signed up, such as a page or a form.")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    token = models.CharField(max_length=64, unique=True, default=_token, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.email

    def unsubscribe(self) -> None:
        if self.status != self.Status.UNSUBSCRIBED:
            self.status = self.Status.UNSUBSCRIBED
            self.unsubscribed_at = timezone.now()
            self.save(update_fields=["status", "unsubscribed_at"])

    def resubscribe(self) -> None:
        self.status = self.Status.ACTIVE
        self.unsubscribed_at = None
        self.save(update_fields=["status", "unsubscribed_at"])


def subscribe(email: str, *, name: str = "", language: str = "", source: str = "") -> NewsletterSubscriber:
    """Add ``email`` to the list, or bring a past subscriber back; the first language and source are kept."""
    email = email.strip().lower()
    row, created = NewsletterSubscriber.objects.get_or_create(
        email=email, defaults={"name": name, "language": language, "source": source})
    if not created and row.status != NewsletterSubscriber.Status.ACTIVE:
        row.resubscribe()
    return row
