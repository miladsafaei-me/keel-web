"""Reusable custom-user foundation.

``AbstractKeelUser`` carries every field + helper of the SignalBots user (UUID pk,
slug, bio, avatar / persona JSON, contact + social fields, and the
``current_session_key`` that powers single-session enforcement) without being tied
to any product. A fresh project can either point ``AUTH_USER_MODEL`` at the
concrete ``keel_web_auth.User`` below, or subclass ``AbstractKeelUser`` in its own
app and add domain fields there.

Domain models that lived alongside the SignalBots user (Coupon / CouponReferral /
Purchase — affiliate coupons + product purchases) are intentionally NOT here; they
stay in the consuming project.
"""
import uuid

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from ..config import web_setting


PHONE_VALIDATOR = RegexValidator(
    regex=r"^\+?[0-9\s\-().]{6,32}$",
    message="Enter a valid phone number (digits, spaces, +, -, parentheses).",
)

TELEGRAM_ID_VALIDATOR = RegexValidator(
    regex=r"^@?[A-Za-z][A-Za-z0-9_]{4,31}$",
    message="Enter a valid Telegram username (5-32 chars, letters/numbers/underscores, optional leading @).",
)


def avatar_upload_to(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    return f"avatars/{instance.pk}/avatar.{ext}"


class AbstractKeelUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to=avatar_upload_to, blank=True, null=True)
    avatar_preset = models.CharField(max_length=32, blank=True)
    avatar_config = models.JSONField(default=dict, blank=True)
    country = models.CharField(max_length=2, blank=True)
    phone = models.CharField(max_length=32, blank=True, validators=[PHONE_VALIDATOR])
    telegram_id = models.CharField(max_length=64, blank=True, validators=[TELEGRAM_ID_VALIDATOR])
    whatsapp_phone = models.CharField(max_length=32, blank=True, validators=[PHONE_VALIDATOR])
    viber_phone = models.CharField(max_length=32, blank=True, validators=[PHONE_VALIDATOR])
    social_links = models.JSONField(default=dict, blank=True)
    role = models.CharField(max_length=100, blank=True)
    # Session key of the account's single active session. A new login (any
    # device/IP) overwrites it and invalidates the prior session; enforced by
    # keel_web.auth.middleware.SingleSessionMiddleware. Blank = no active session.
    current_session_key = models.CharField(max_length=40, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.username
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        full = (self.get_full_name() or "").strip()
        return full or self.username or self.email

    @property
    def initials(self):
        source = (self.get_full_name() or self.username or self.email or "?").strip()
        parts = [p for p in source.replace("@", " ").split() if p]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][:1] + parts[-1][:1]).upper()

    @property
    def country_name(self):
        if not self.country:
            return ""
        try:
            import pycountry
            entry = pycountry.countries.get(alpha_2=self.country)
            return entry.name if entry else self.country
        except Exception:
            return self.country

    @property
    def avatar_display_url(self):
        if self.avatar:
            try:
                return self.avatar.url
            except ValueError:
                pass
        return ""

    @property
    def avatar_persona_layers(self):
        """Ordered list of (folder, file) tuples for stacked SVG rendering.

        Returns [] when the user has no persona configured. Composition order is
        bottom→top: background, body, skin, hair, facial hair, mouth, nose, eyes.
        """
        cfg = self.avatar_config or {}
        order = (
            ("Background", cfg.get("bg")),
            ("Body",       cfg.get("body")),
            ("Skin",       cfg.get("skin")),
            ("Hair",       cfg.get("hair")),
            ("FacialHair", cfg.get("facialHair")),
            ("Mouth",      cfg.get("mouth")),
            ("Nose",       cfg.get("nose")),
            ("Eyes",       cfg.get("eyes")),
        )
        return [(folder, value) for folder, value in order if value]


class User(AbstractKeelUser):
    """Concrete drop-in user. Point ``AUTH_USER_MODEL`` at ``keel_web_auth.User``.

    The table name is a config seam: set ``KEEL_WEB["user_db_table"]`` to an
    existing table (e.g. ``"users_user"``) to adopt this model into a project
    that already has a user table, with only a metadata-level migration.
    """

    class Meta(AbstractKeelUser.Meta):
        abstract = False
        db_table = web_setting("user_db_table")
