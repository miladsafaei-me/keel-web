"""Account-settings forms for the client panel (profile / email / password / avatar).

These are the domain-neutral half of the SignalBots ``users.forms``. The public
auth forms there (``CustomLoginForm`` / ``CustomSignupForm``, which pull in an
anti-spam service) and ``CouponForm`` (affiliate monetization) stay in the host —
they are Bucket-0 domain code.
"""
from __future__ import annotations

import json

import pycountry
from allauth.account.models import EmailAddress
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .personas import (
    PERSONA_PRESETS,
    is_valid_config,
    preset_config,
)
from .phone_helpers import (
    DEFAULT_REGION,
    country_data,
    normalize_to_e164,
    parse_e164,
)


User = get_user_model()


PHONE_FIELDS = (
    ("phone", "phone_country", "phone_national"),
    ("whatsapp_phone", "whatsapp_country", "whatsapp_national"),
    ("viber_phone", "viber_country", "viber_national"),
)


def country_choices():
    items = sorted(
        ((c.alpha_2, c.name) for c in pycountry.countries),
        key=lambda x: x[1],
    )
    return [("", _("Select your country"))] + items


def _digits_only_input():
    return forms.TextInput(
        attrs={
            "class": "ta-input phone-national-input",
            "autocomplete": "tel-national",
            "inputmode": "numeric",
            "pattern": "[0-9]*",
            "data-phone-input": "1",
        }
    )


class ProfileForm(forms.ModelForm):
    """Edit name, country, and contact details (phone/WhatsApp/Viber/Telegram)."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": "ta-input", "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "ta-input", "autocomplete": "family-name"}),
    )
    country = forms.ChoiceField(
        choices=(),
        required=False,
        widget=forms.Select(attrs={"class": "ta-select"}),
    )
    telegram_id = forms.CharField(
        max_length=64,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "ta-input",
                "placeholder": "@username",
                "pattern": r"@?[A-Za-z][A-Za-z0-9_]{4,31}",
                "autocapitalize": "off",
                "autocorrect": "off",
                "spellcheck": "false",
            }
        ),
    )

    phone_country = forms.CharField(required=False, widget=forms.HiddenInput())
    phone_national = forms.CharField(required=False, widget=_digits_only_input())
    whatsapp_country = forms.CharField(required=False, widget=forms.HiddenInput())
    whatsapp_national = forms.CharField(required=False, widget=_digits_only_input())
    viber_country = forms.CharField(required=False, widget=forms.HiddenInput())
    viber_national = forms.CharField(required=False, widget=_digits_only_input())

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "country",
            "telegram_id",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["country"].choices = country_choices()
        instance = kwargs.get("instance") or self.instance
        default_region = (instance.country or DEFAULT_REGION).upper() if instance else DEFAULT_REGION
        for stored_attr, country_field, national_field in PHONE_FIELDS:
            stored = getattr(instance, stored_attr, "") if instance else ""
            region, national = parse_e164(stored)
            if not self.is_bound:
                self.initial.setdefault(country_field, region or default_region)
                self.initial.setdefault(national_field, national)

    def clean(self):
        cleaned = super().clean()
        for stored_attr, country_field, national_field in PHONE_FIELDS:
            country_val = (cleaned.get(country_field) or "").strip().upper()
            national_raw = (cleaned.get(national_field) or "").strip()
            national_digits = "".join(c for c in national_raw if c.isdigit()).lstrip("0")
            if not national_digits:
                cleaned[stored_attr] = ""
                continue
            try:
                cleaned[stored_attr] = normalize_to_e164(country_val, national_digits)
            except ValidationError as exc:
                self.add_error(national_field, exc)
                cleaned[stored_attr] = ""
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        for stored_attr, _country_field, _national_field in PHONE_FIELDS:
            setattr(instance, stored_attr, self.cleaned_data.get(stored_attr, ""))
        if commit:
            instance.save()
        return instance


class EmailChangeForm(forms.Form):
    email = forms.EmailField(
        label=_("New email"),
        widget=forms.EmailInput(
            attrs={"class": "ta-input", "autocomplete": "email"}
        ),
    )
    current_password = forms.CharField(
        label=_("Current password"),
        widget=forms.PasswordInput(
            attrs={"class": "ta-input", "autocomplete": "current-password"}
        ),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        pw = self.cleaned_data["current_password"]
        if not self.user.check_password(pw):
            raise ValidationError(_("Password is incorrect."))
        return pw

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if email == (self.user.email or "").lower():
            raise ValidationError(_("This is already your email address."))
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.user.pk)
        if qs.exists():
            raise ValidationError(_("Another account is using this email."))
        return email

    @transaction.atomic
    def save(self):
        new_email = self.cleaned_data["email"]
        old_email = self.user.email
        self.user.email = new_email
        self.user.save(update_fields=["email"])
        EmailAddress.objects.filter(user=self.user, primary=True).update(primary=False)
        existing = (
            EmailAddress.objects.filter(user=self.user, email__iexact=new_email)
            .order_by("pk")
            .first()
        )
        if existing:
            existing.email = new_email
            existing.primary = True
            existing.verified = False
            existing.save(update_fields=["email", "primary", "verified"])
        else:
            EmailAddress.objects.create(
                user=self.user, email=new_email, primary=True, verified=False
            )
        return self.user, old_email


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        label=_("Current password"),
        widget=forms.PasswordInput(
            attrs={"class": "ta-input", "autocomplete": "current-password"}
        ),
    )
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(
            attrs={"class": "ta-input", "autocomplete": "new-password"}
        ),
    )
    new_password2 = forms.CharField(
        label=_("Confirm new password"),
        widget=forms.PasswordInput(
            attrs={"class": "ta-input", "autocomplete": "new-password"}
        ),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        pw = self.cleaned_data["current_password"]
        if not self.user.check_password(pw):
            raise ValidationError(_("Password is incorrect."))
        return pw

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            self.add_error("new_password2", _("The two new passwords do not match."))
        if p1:
            try:
                validate_password(p1, user=self.user)
            except ValidationError as exc:
                self.add_error("new_password1", exc)
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data["new_password1"])
        self.user.save(update_fields=["password"])
        return self.user


class AvatarForm(forms.Form):
    """
    One form, three input modes:

    - ``avatar`` (image upload) — wins over everything else
    - ``persona`` (JSON config) — composes a layered SVG persona
    - ``preset`` (key from PERSONA_PRESETS) — convenience selector that resolves to a config
    - ``clear=1`` — removes any current avatar/persona
    """

    avatar = forms.ImageField(required=False)
    preset = forms.CharField(required=False, max_length=32)
    persona = forms.CharField(required=False, widget=forms.HiddenInput())
    clear = forms.BooleanField(required=False)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_preset(self):
        value = (self.cleaned_data.get("preset") or "").strip()
        if value and preset_config(value) is None:
            raise ValidationError(_("Invalid avatar preset."))
        return value

    def clean_persona(self):
        raw = (self.cleaned_data.get("persona") or "").strip()
        if not raw:
            return {}
        try:
            cfg = json.loads(raw)
        except ValueError:
            raise ValidationError(_("Invalid avatar configuration."))
        if not is_valid_config(cfg):
            raise ValidationError(_("Invalid avatar configuration."))
        return cfg

    def clean(self):
        cleaned = super().clean()
        if not (
            cleaned.get("avatar")
            or cleaned.get("preset")
            or cleaned.get("persona")
            or cleaned.get("clear")
        ):
            raise ValidationError(
                _("Upload a photo, pick a persona, or clear the avatar.")
            )
        return cleaned

    def save(self):
        cleaned = self.cleaned_data
        if cleaned.get("clear"):
            if self.user.avatar:
                self.user.avatar.delete(save=False)
            self.user.avatar = None
            self.user.avatar_preset = ""
            self.user.avatar_config = {}
        elif cleaned.get("avatar"):
            if self.user.avatar:
                self.user.avatar.delete(save=False)
            self.user.avatar = cleaned["avatar"]
            self.user.avatar_preset = ""
            self.user.avatar_config = {}
        elif cleaned.get("persona"):
            if self.user.avatar:
                self.user.avatar.delete(save=False)
            self.user.avatar = None
            self.user.avatar_preset = ""
            self.user.avatar_config = cleaned["persona"]
        elif cleaned.get("preset"):
            cfg = preset_config(cleaned["preset"])
            if self.user.avatar:
                self.user.avatar.delete(save=False)
            self.user.avatar = None
            self.user.avatar_preset = cleaned["preset"]
            self.user.avatar_config = cfg or {}
        self.user.save(update_fields=["avatar", "avatar_preset", "avatar_config"])
        return self.user
