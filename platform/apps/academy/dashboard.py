"""Contributions d'Academy au tableau de bord, à la cloche et à la recherche (données réelles)."""

import datetime as dt

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import number_format
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.utils.translation import ngettext

from apps.core.permissions import request_has_perm

from . import services
from .models import Order

WAITING = (Order.Status.AWAITING_PAYMENT, Order.Status.PAYMENT_PENDING)


def academy_section(request):
    if not request_has_perm(request, "academy.view"):
        return None
    shortcuts = [{"order": 40, "icon": "bag", "label": _("See the offers"),
                  "url": reverse("academy:offer_list"), "tone": "slate"}]
    if not request_has_perm(request, "payments.view_orders"):
        return {"order": 30, "shortcuts": shortcuts}
    orders = Order.objects.filter(organization=request.organization)
    orders_url = reverse("academy:order_list")
    to_check = orders.filter(status__in=WAITING).count()
    week_ago = timezone.now() - dt.timedelta(days=7)
    return {
        "order": 30,
        "priorities": [{
            "rank": 15,
            "count": to_check,
            "label": ngettext("Payment to check", "Payments to check", to_check),
            "hint": _("Orders waiting for a manual confirmation"),
            "url": f"{orders_url}?status=awaiting_payment",
            "action": _("Open the orders"),
            "icon": "cash-coin",
            "urgent": False,
        }],
        "kpis": [{
            "rank": 40,
            "icon": "cart3",
            "value": orders.filter(created_at__gte=week_ago).count(),
            "label": _("Orders (7 days)"),
            "url": orders_url,
        }],
        "shortcuts": shortcuts,
    }


def academy_notifications(request):
    if not request_has_perm(request, "payments.view_orders"):
        return []
    waiting = Order.objects.filter(organization=request.organization, status__in=WAITING).count()
    if not waiting:
        return []
    return [{
        "rank": 15,
        "count": waiting,
        "label": ngettext("%(n)s payment to check", "%(n)s payments to check", waiting) % {"n": waiting},
        "url": f"{reverse('academy:order_list')}?status=awaiting_payment",
        "icon": "cash-coin",
    }]


def academy_search(request, query):
    groups = []
    if request_has_perm(request, "payments.view_orders"):
        terms = Q(user__email__icontains=query) | Q(user__full_name__icontains=query) | Q(offer__name_fr__icontains=query)
        number = query.lstrip("#").removeprefix("N°").strip()
        if number.isdigit():
            terms |= Q(pk=int(number))
        found = (
            Order.objects.filter(organization=request.organization)
            .filter(terms)
            .select_related("user", "offer")
            .order_by("-created_at")
        )
        groups.append({
            "order": 30,
            "title": _("Orders"),
            "icon": "cash-coin",
            "results": [
                {
                    "title": _("Order no. %(n)s") % {"n": order.pk},
                    "meta": f"{order.user} · {order.get_status_display()}",
                    "url": reverse("academy:order_detail", args=[order.pk]),
                }
                for order in found[:8]
            ],
            "total": found.count(),
            "more_url": reverse("academy:order_list"),
        })
    if request_has_perm(request, "academy.view"):
        offers = services.purchasable_offers(request.organization).filter(
            Q(name_fr__icontains=query) | Q(name_en__icontains=query) | Q(program__title_fr__icontains=query)
        )
        groups.append({
            "order": 40,
            "title": _("Offers"),
            "icon": "bag",
            "results": [
                {"title": str(offer), "meta": f"{number_format(offer.price, 2)} {offer.currency}",
                 "url": reverse("academy:offer_detail", args=[offer.pk])}
                for offer in offers[:8]
            ],
            "total": offers.count(),
            "more_url": reverse("academy:offer_list"),
        })
    return groups


AUDIT_ACTIONS = {
    "academy_order_created": (gettext_lazy("Order created"), "new"),
    "academy_payment_confirmed": (gettext_lazy("Payment confirmed by hand"), "payment"),
    "academy_order_cancelled": (gettext_lazy("Order cancelled"), "change"),
    "academy_order_refunded": (gettext_lazy("Order refunded"), "payment"),
    "academy_access_revoked": (gettext_lazy("Access revoked"), "change"),
}
