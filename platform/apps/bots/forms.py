from __future__ import annotations

from decimal import Decimal

from django import forms
from django.forms import modelformset_factory
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.forms import BootstrapFormMixin
from apps.core.templatetags.systemc import plain_decimal

from .models import AccountType, BotStatus, BotUser, ConfigurationVersion, ParameterDefinition, RobotType

DATE_INPUT = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
NO_SECRET_HELP = _("Never write a Deriv token, password or API key here.")


class BotUserForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = BotUser
        fields = ["wants_bot", "robot_type", "vps_label", "admin_note"]
        widgets = {"admin_note": forms.Textarea(attrs={"rows": 3, "maxlength": 1000})}
        help_texts = {"admin_note": NO_SECRET_HELP}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["robot_type"].required = False
        self.fields["robot_type"].choices = [("", _("Not chosen yet"))] + list(RobotType.choices)


class BotUserCreateForm(BotUserForm):
    affiliate = forms.ModelChoiceField(label=_("Affiliate"), queryset=None)

    class Meta(BotUserForm.Meta):
        fields = ["affiliate"] + BotUserForm.Meta.fields

    def __init__(self, *args, affiliates, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["affiliate"].queryset = affiliates
        self.fields["affiliate"].widget.attrs["class"] = "form-select"
        self.order_fields(["affiliate"] + BotUserForm.Meta.fields)


def parameter_field_name(key: str) -> str:
    return f"param_{key}"


class VersionForm(BootstrapFormMixin, forms.ModelForm):
    """Brouillon de version : champs fixes + un champ numérique par paramètre autorisé."""

    class Meta:
        model = ConfigurationVersion
        fields = ["account_type", "reference_capital", "currency", "admin_note"]
        widgets = {"admin_note": forms.Textarea(attrs={"rows": 3, "maxlength": 1000})}
        help_texts = {
            "reference_capital": _("Declared amount. Never synchronised with an account balance."),
            "admin_note": NO_SECRET_HELP,
        }

    def __init__(self, *args, definitions, can_manage_real: bool, **kwargs):
        super().__init__(*args, **kwargs)
        self.definitions = list(definitions)
        if not can_manage_real:
            self.fields["account_type"].choices = [(AccountType.DEMO, AccountType.DEMO.label)]
            self.fields["account_type"].help_text = _("Only a CRM administrator can declare a real account.")
        existing = {p.key: p.value for p in self.instance.parameters.all()} if self.instance.pk else {}
        for definition in self.definitions:
            name = parameter_field_name(definition.key)
            help_parts = []
            if definition.unit:
                help_parts.append(str(_("Unit: %(unit)s")) % {"unit": definition.unit})
            if not definition.verified:
                help_parts.append(str(_("Not yet verified on the real files.")))
            self.fields[name] = forms.DecimalField(
                label=definition.key,
                required=False,
                max_digits=18,
                decimal_places=6,
                min_value=definition.min_value,
                max_value=definition.max_value,
                help_text=" ".join(help_parts),
                widget=forms.NumberInput(attrs={"class": "form-control", "step": "any", "inputmode": "decimal"}),
            )
            if definition.key in existing:
                self.fields[name].initial = plain_decimal(existing[definition.key])

    def clean_currency(self):
        return (self.cleaned_data.get("currency") or "").strip().upper()

    def parameter_values(self) -> dict[str, Decimal | None]:
        return {d.key: self.cleaned_data.get(parameter_field_name(d.key)) for d in self.definitions}

    def parameter_fields(self):
        return [self[parameter_field_name(d.key)] for d in self.definitions]

    def definition_for(self, key):
        return next((d for d in self.definitions if d.key == key), None)


class RealDeclarationForm(BootstrapFormMixin, forms.Form):
    confirmed = forms.BooleanField(label=_("I confirm the declaration below."), required=True)
    declared_on = forms.DateField(label=_("Declaration date"), widget=DATE_INPUT)
    note = forms.CharField(
        label=_("Administrative note"), max_length=500, widget=forms.Textarea(attrs={"rows": 3}), help_text=NO_SECRET_HELP
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["declared_on"].initial = timezone.localdate()

    def clean_declared_on(self):
        value = self.cleaned_data["declared_on"]
        if value > timezone.localdate():
            raise forms.ValidationError(_("The date cannot be in the future."))
        return value


class DeclareAppliedForm(BootstrapFormMixin, forms.Form):
    applied_on = forms.DateField(label=_("Date applied on the VPS"), widget=DATE_INPUT)
    note = forms.CharField(
        label=_("Note"), max_length=500, required=False, widget=forms.Textarea(attrs={"rows": 2}), help_text=NO_SECRET_HELP
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["applied_on"].initial = timezone.localdate()

    def clean_applied_on(self):
        value = self.cleaned_data["applied_on"]
        if value > timezone.localdate():
            raise forms.ValidationError(_("The date cannot be in the future."))
        return value


class ReasonForm(BootstrapFormMixin, forms.Form):
    reason = forms.CharField(label=_("Reason"), max_length=300, help_text=NO_SECRET_HELP)


class ParameterDefinitionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ParameterDefinition
        fields = ["enabled", "verified", "unit", "min_value", "max_value", "verification_reference"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("verified") and not (cleaned.get("verification_reference") or "").strip():
            self.add_error("verification_reference", _("Indicate the file and line checked before marking it verified."))
        low, high = cleaned.get("min_value"), cleaned.get("max_value")
        if low is not None and high is not None and low > high:
            self.add_error("max_value", _("The maximum must be greater than or equal to the minimum."))
        return cleaned


ParameterDefinitionFormSet = modelformset_factory(ParameterDefinition, form=ParameterDefinitionForm, extra=0)


class BotFilterForm(forms.Form):
    q = forms.CharField(required=False, label=_("Search"))
    status = forms.ChoiceField(required=False, label=_("Status"), choices=[("", _("All statuses"))] + list(BotStatus.choices))
    robot_type = forms.ChoiceField(required=False, label=_("Robot"), choices=[("", _("All robots"))] + list(RobotType.choices))
    account_type = forms.ChoiceField(
        required=False, label=_("Account type"), choices=[("", _("All accounts"))] + list(AccountType.choices)
    )
    alert = forms.ChoiceField(
        required=False,
        label=_("Alert"),
        choices=[
            ("", _("No filter")),
            ("to_apply", _("Configuration to apply")),
            ("modification_pending", _("Change request pending")),
            ("configuration_review", _("Configuration to review")),
        ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-select form-select-sm" if isinstance(field.widget, forms.Select) else "form-control form-control-sm"
            )
