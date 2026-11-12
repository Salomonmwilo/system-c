"""Contribution d'Academy au tableau de bord : paiements confirmés à la main ce mois-ci."""

from decimal import Decimal

from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from apps.core.permissions import request_has_perm

from .models import Order, OrderAudit


def academy_section(request):
    if not request_has_perm(request, "payments.view_orders"):
        return None
    now = timezone.localtime()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    history = OrderAudit.objects.filter(order__organization=request.organization, created_at__gte=month_start)
    confirmed = history.filter(action=OrderAudit.Action.PAYMENT_VERIFIED)
    refunds = history.filter(action__in=(OrderAudit.Action.REFUNDED, OrderAudit.Action.PARTIAL_REFUND))
    by_currency = {}
    for row in confirmed.values("currency").annotate(total=Sum("amount")):
        by_currency[row["currency"]] = row["total"] or Decimal("0")
    for row in refunds.values("currency").annotate(total=Sum("amount")):
        by_currency[row["currency"]] = by_currency.get(row["currency"], Decimal("0")) - (row["total"] or Decimal("0"))
    to_check = Order.objects.filter(
        organization=request.organization, status__in=(Order.Status.AWAITING_PAYMENT, Order.Status.PAYMENT_PENDING)
    ).count()
    orders_url = reverse("academy:order_list")
    priorities = [{
        "rank": 15,
        "count": to_check,
        "label": ngettext("Payment to check", "Payments to check", to_check),
        "hint": _("Orders waiting for a manual confirmation"),
        "url": f"{orders_url}?status=awaiting_payment",
        "action": _("Open the orders"),
        "urgent": False,
    }]
    return {
        "order": 30,
        "priorities": priorities,
        "widgets": [{
            "slot": "side", "order": 20, "template": "academy/dashboard_payments.html",
            "context": {
                "totals": sorted(by_currency.items()),
                "confirmations": confirmed.count(),
                "month": now,
                "url": orders_url,
            },
        }],
    }
