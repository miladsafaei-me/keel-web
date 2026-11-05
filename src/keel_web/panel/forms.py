from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm, UserCreationForm
from django.contrib.auth.models import Group

from keel_web.admin_shell.forms import PanelFormMixin


class PanelLoginForm(PanelFormMixin, AuthenticationForm):
    pass


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
