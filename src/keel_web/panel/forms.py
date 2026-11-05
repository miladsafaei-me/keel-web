from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm, UserCreationForm
from django.contrib.auth.models import Group

from keel_web.admin_shell.forms import PanelFormMixin


class PanelLoginForm(PanelFormMixin, AuthenticationForm):
    """Signs in with the username or the account's email."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email or username"

    def clean(self):
        typed = (self.data.get(self.add_prefix("username")) or "").strip()
        if "@" in typed:
            model = get_user_model()
            if not model.objects.filter(**{model.USERNAME_FIELD: typed}).exists():
                match = model.objects.filter(email__iexact=typed).order_by("pk").first()
                if match:
                    self.cleaned_data["username"] = match.get_username()
        return super().clean()


class PanelPasswordChangeForm(PanelFormMixin, PasswordChangeForm):
    pass


class PanelSetPasswordForm(PanelFormMixin, SetPasswordForm):
    pass


class UserEditForm(PanelFormMixin, forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False,
                                            widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email", "is_active", "is_staff", "is_superuser", "groups")
        help_texts = {
            "is_staff": "Can sign in to this panel.",
            "is_superuser": "Sees every page of the panel, users included.",
            "is_active": "Off blocks sign-in without deleting the account.",
        }

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor

    def clean(self):
        data = super().clean()
        if self.editor and self.instance.pk == self.editor.pk:
            if not data.get("is_active") or not data.get("is_superuser") or not data.get("is_staff"):
                raise forms.ValidationError("You cannot lock yourself out: keep your own account active, staff and superuser.")
        return data


class UserCreateForm(PanelFormMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email", "is_staff", "is_superuser")


class SignupForm(PanelFormMixin, forms.Form):
    """A member account: the email is the username. ``website`` is a trap only bots fill in."""

    name = forms.CharField(max_length=150, label="Your name")
    email = forms.EmailField(label="Email")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Password again", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    newsletter = forms.BooleanField(required=False, initial=True, label="Send me the newsletter")
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    def __init__(self, *args, newsletter=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not newsletter:
            del self.fields["newsletter"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        model = get_user_model()
        if model.objects.filter(email__iexact=email).exists() or model.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("This email already has an account. Sign in instead.")
        return email

    def clean(self):
        from django.contrib.auth.password_validation import validate_password

        data = super().clean()
        if data.get("password1") and data.get("password1") != data.get("password2"):
            self.add_error("password2", "The two passwords differ.")
        elif data.get("password1"):
            try:
                validate_password(data["password1"])
            except forms.ValidationError as error:
                self.add_error("password1", error)
        return data

    def save(self):
        name = self.cleaned_data["name"].strip()
        first, _, last = name.partition(" ")
        return get_user_model().objects.create_user(
            username=self.cleaned_data["email"], email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"], first_name=first[:150], last_name=last[:150])
