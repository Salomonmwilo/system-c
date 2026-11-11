from decimal import Decimal

from django import forms
from django.utils.formats import number_format
from django.utils.translation import gettext_lazy as _

from apps.core.forms import BootstrapFormMixin

NO_BANK_DATA_HELP = _("Never enter a card number, bank details, password or access key.")


class OrderForm(BootstrapFormMixin, forms.Form):
    acknowledge = forms.BooleanField(
        label=_("I have read the notice above: this programme is educational, trading carries a risk of loss, "
                "no result is guaranteed and no personal advice is given."),
    )


class BuyerCancelForm(BootstrapFormMixin, forms.Form):
    prefix = "cancel"

    reason = forms.CharField(label=_("Reason (optional)"), max_length=500, required=False)


class ConfirmPaymentForm(BootstrapFormMixin, forms.Form):
    prefix = "confirm"

    received = forms.BooleanField()
    reference = forms.CharField(
        label=_("Transaction reference"), max_length=100, required=False, help_text=NO_BANK_DATA_HELP
    )
    note = forms.CharField(
        label=_("Verification note"),
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text=_("How the payment was checked, for example the statement line or the receipt seen."),
    )

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, **kwargs)
        if order is not None:
            self.fields["received"].label = _("I have checked that %(amount)s %(currency)s was received for this order.") % {
                "amount": number_format(order.price, 2, force_grouping=True),
                "currency": order.currency,
            }
        for name in ("reference",):
            self.fields[name].widget.attrs.update({"autocomplete": "off", "spellcheck": "false"})


class AdminCancelForm(BootstrapFormMixin, forms.Form):
    prefix = "cancel"

    reason = forms.CharField(label=_("Reason for cancelling"), max_length=500)


class RefundForm(BootstrapFormMixin, forms.Form):
    prefix = "refund"

    amount = forms.DecimalField(label=_("Amount refunded"), max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    reference = forms.CharField(
        label=_("Refund reference"), max_length=100, required=False, help_text=NO_BANK_DATA_HELP
    )
    reason = forms.CharField(label=_("Justification"), max_length=500, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.order = order
        if order is not None:
            remaining = order.remaining_refundable
            self.fields["amount"].widget.attrs.update({"max": str(remaining), "inputmode": "decimal"})
            self.fields["amount"].help_text = _(
                "Refunding %(remaining)s %(currency)s in total is a full refund and removes access immediately. "
                "A smaller amount is a partial refund: access is kept."
            ) % {"remaining": number_format(remaining, 2, force_grouping=True), "currency": order.currency}
            self.initial.setdefault("amount", remaining)
        self.fields["reference"].widget.attrs.update({"autocomplete": "off", "spellcheck": "false"})

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if self.order is not None and amount > self.order.remaining_refundable:
            raise forms.ValidationError(
                _("At most %(remaining)s %(currency)s can still be refunded.")
                % {"remaining": number_format(self.order.remaining_refundable, 2, force_grouping=True),
                   "currency": self.order.currency}
            )
        return amount


class OrderFilterForm(forms.Form):
    status = forms.ChoiceField(label=_("Status"), required=False)

    def __init__(self, *args, **kwargs):
        from .models import Order

        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [("", _("All statuses"))] + list(Order.Status.choices)
        self.fields["status"].widget.attrs["class"] = "form-select form-select-sm"
