from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.forms import BootstrapFormMixin

from .models import TRACK_FIELDS, Affiliate, FollowUp, Interaction, ReferralLink, TrackEvent

DATE_INPUT = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
DATETIME_INPUT = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")


def organization_members(organization):
    return get_user_model().objects.filter(memberships__organization=organization, is_active=True).distinct().order_by("full_name")


class AffiliateForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Affiliate
        fields = ["display_name", "email", "phone", "country", "preferred_language", "status", "referral_link", "assigned_to"]
        help_texts = {
            "country": _("Two-letter ISO code, for example CD, FR or BE."),
            "assigned_to": _("Person in charge of following up with this affiliate."),
        }

    def __init__(self, *args, organization, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.fields["referral_link"].queryset = ReferralLink.objects.filter(organization=organization, is_active=True)
        self.fields["assigned_to"].queryset = organization_members(organization)
        self.fields["country"].widget.attrs.update({"maxlength": 2, "autocomplete": "off"})
        # Saisie pour une autre personne : pas de remplissage automatique avec les données de l'administrateur.
        self.fields["email"].widget.attrs.update({"autocomplete": "off", "spellcheck": "false"})
        self.fields["phone"].widget.input_type = "tel"
        self.fields["phone"].widget.attrs.update({"autocomplete": "off", "inputmode": "tel"})

    def clean_country(self):
        return (self.cleaned_data.get("country") or "").strip().upper()

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email:
            duplicates = Affiliate.objects.filter(organization=self.organization, email__iexact=email)
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise forms.ValidationError(_("Another affiliate already uses this email address."))
        return email


class TrackForm(BootstrapFormMixin, forms.Form):
    value = forms.ChoiceField(label=_("Status"))
    declared_on = forms.DateField(label=_("Date"), widget=DATE_INPUT)
    source = forms.ChoiceField(label=_("Source"), choices=TrackEvent.Source.choices, initial=TrackEvent.Source.ADMINISTRATOR)
    note = forms.CharField(label=_("Note"), max_length=500, required=False)

    def __init__(self, *args, track: str, current: str | None = None, **kwargs):
        kwargs.setdefault("prefix", f"track-{track}")
        super().__init__(*args, **kwargs)
        self.track = track
        self.fields["value"].choices = TRACK_FIELDS[track][2].choices
        if current:
            self.fields["value"].initial = current
        self.fields["declared_on"].initial = timezone.localdate()

    def clean_declared_on(self):
        value = self.cleaned_data["declared_on"]
        if value > timezone.localdate():
            raise forms.ValidationError(_("The date cannot be in the future."))
        return value


class InteractionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Interaction
        fields = ["kind", "occurred_at", "summary"]
        widgets = {"occurred_at": DATETIME_INPUT, "summary": forms.Textarea(attrs={"rows": 3, "maxlength": 2000})}
        help_texts = {"summary": _("Never write a password, token or API key here.")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["occurred_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["occurred_at"].initial = timezone.localtime().strftime("%Y-%m-%dT%H:%M")

    def clean_occurred_at(self):
        value = self.cleaned_data["occurred_at"]
        if value > timezone.now() + timezone.timedelta(minutes=5):
            raise forms.ValidationError(_("The date cannot be in the future."))
        return value


class FollowUpForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ["title", "due_on", "assigned_to", "note"]
        widgets = {"due_on": DATE_INPUT}

    def __init__(self, *args, organization, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = organization_members(organization)
        self.fields["due_on"].initial = timezone.localdate()


class ReferralLinkForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ReferralLink
        fields = ["label", "url", "is_active"]
        help_texts = {"url": _("Public HTTPS link only. A referral link never contains a password or token.")}

    def clean_url(self):
        url = self.cleaned_data["url"]
        if not url.lower().startswith("https://"):
            raise forms.ValidationError(_("The link must start with https://."))
        return url


class AffiliateFilterForm(forms.Form):
    q = forms.CharField(required=False, label=_("Search"))
    status = forms.ChoiceField(required=False, label=_("Status"), choices=[("", _("All statuses"))] + list(Affiliate.Status.choices))
    registration = forms.ChoiceField(
        required=False, label=_("Deriv registration"), choices=[("", _("All"))] + list(Affiliate.Registration.choices)
    )
    verification = forms.ChoiceField(
        required=False, label=_("Verification"), choices=[("", _("All"))] + list(Affiliate.Verification.choices)
    )
    alert = forms.ChoiceField(
        required=False,
        label=_("Alert"),
        choices=[
            ("", _("No filter")),
            ("contact_stale", _("No recent contact")),
            ("registration_stuck", _("Registration unfinished")),
            ("verification_stuck", _("Verification unfinished")),
        ],
    )
    archived = forms.BooleanField(required=False, label=_("Show archived"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else (
                "form-select form-select-sm" if isinstance(field.widget, forms.Select) else "form-control form-control-sm"
            )
            field.widget.attrs["class"] = css
