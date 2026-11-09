from __future__ import annotations

import hashlib

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from .models import Language, OrganizationSettings, Role, User, UserManager


class BootstrapFormMixin:
    """Applique les classes Bootstrap aux widgets, sans JavaScript."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")
        for name, field in self.fields.items():
            if field.help_text:
                field.widget.attrs.setdefault("aria-describedby", f"{self[name].auto_id}_help")

    def full_clean(self):
        super().full_clean()
        # Accessibilité : signale les champs en erreur et relie aide et message d'erreur.
        for name, field in self.fields.items():
            auto_id = self[name].auto_id
            described = []
            if field.help_text:
                described.append(f"{auto_id}_help")
            if name in self.errors:
                css = field.widget.attrs.get("class", "")
                if "is-invalid" not in css:
                    field.widget.attrs["class"] = f"{css} is-invalid".strip()
                field.widget.attrs["aria-invalid"] = "true"
                described.append(f"{auto_id}_error")
            if described:
                field.widget.attrs["aria-describedby"] = " ".join(described)


def _key(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"systemc:login:{prefix}:{digest}"


def client_ip(request) -> str:
    return request.META.get("REMOTE_ADDR", "") if request is not None else ""


class LoginForm(BootstrapFormMixin, forms.Form):
    """Connexion par adresse et mot de passe, avec limitation des tentatives.

    Le message d'erreur est identique quel que soit le motif d'échec, pour ne pas
    révéler l'existence d'un compte.
    """

    email = forms.EmailField(label=_("Email address"), widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}))
    password = forms.CharField(
        label=_("Password"), strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"})
    )

    error_messages = {
        "invalid_login": _("Incorrect email address or password."),
        "throttled": _("Too many unsuccessful attempts. Please try again later."),
        "inactive": _("Incorrect email address or password."),
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def _is_throttled(self, email_key: str, ip_key: str) -> bool:
        return (cache.get(email_key, 0) >= settings.LOGIN_MAX_ATTEMPTS_PER_ACCOUNT) or (
            cache.get(ip_key, 0) >= settings.LOGIN_MAX_ATTEMPTS_PER_IP
        )

    @staticmethod
    def _increment(key: str) -> None:
        cache.add(key, 0, settings.LOGIN_LOCKOUT_SECONDS)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, settings.LOGIN_LOCKOUT_SECONDS)

    def clean(self):
        email = UserManager.normalize_login(self.cleaned_data.get("email", ""))
        password = self.cleaned_data.get("password")
        if not email or not password:
            return self.cleaned_data
        email_key = _key("account", email)
        ip_key = _key("ip", client_ip(self.request))
        if self._is_throttled(email_key, ip_key):
            self.throttled = True
            raise forms.ValidationError(self.error_messages["throttled"], code="throttled")
        user = authenticate(self.request, username=email, password=password)
        if user is None or not user.is_active:
            self._increment(email_key)
            self._increment(ip_key)
            raise forms.ValidationError(self.error_messages["invalid_login"], code="invalid_login")
        cache.delete(email_key)
        self.user_cache = user
        return self.cleaned_data

    def get_user(self):
        return self.user_cache


ROLE_CHOICES = Role.choices


class MemberCreateForm(BootstrapFormMixin, forms.Form):
    email = forms.EmailField(label=_("Email address"))
    full_name = forms.CharField(label=_("Full name"), max_length=150)
    preferred_language = forms.ChoiceField(label=_("Language"), choices=Language.choices, initial=Language.FR)
    roles = forms.MultipleChoiceField(
        label=_("Roles"), choices=ROLE_CHOICES, widget=forms.CheckboxSelectMultiple, required=True
    )
    password = forms.CharField(
        label=_("Initial password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_("At least 12 characters. Share it through a separate channel; the person should change it after signing in."),
    )

    def clean_email(self):
        email = UserManager.normalize_login(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("This account cannot be created with this email address."))
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        if password:
            candidate = User(email=cleaned.get("email", ""), full_name=cleaned.get("full_name", ""))
            try:
                validate_password(password, candidate)
            except forms.ValidationError as exc:
                self.add_error("password", exc)
        return cleaned


class MemberRolesForm(BootstrapFormMixin, forms.Form):
    roles = forms.MultipleChoiceField(
        label=_("Roles"), choices=ROLE_CHOICES, widget=forms.CheckboxSelectMultiple, required=False
    )


class ThresholdsForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = OrganizationSettings
        fields = [
            "contact_stale_days",
            "modification_pending_days",
            "configuration_review_days",
            "registration_stuck_days",
            "verification_stuck_days",
            "default_currency",
        ]

    def clean_default_currency(self):
        value = (self.cleaned_data.get("default_currency") or "").strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise forms.ValidationError(_("Use a three-letter ISO currency code, for example USD."))
        return value
