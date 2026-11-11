from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from apps.core.permissions import OrgPermissionRequiredMixin, get_for_org, request_has_perm

from . import services
from .access import can_access_resource
from .forms import AdminCancelForm, BuyerCancelForm, ConfirmPaymentForm, OrderFilterForm, OrderForm, RefundForm
from .models import Order, Program, Resource


def _report(request, exc: Exception) -> None:
    if isinstance(exc, ValidationError):
        for message in exc.messages:
            messages.error(request, message)
    else:
        messages.error(request, _("You are not allowed to perform this action."))


def _included_resources(offer, user):
    """Ressources de l'offre, avec leur disponibilité réelle et l'accès de la personne."""
    rows = []
    for resource in offer.resources.exclude(status=Resource.Status.ARCHIVED).order_by("position"):
        available = resource.status == Resource.Status.PUBLISHED and resource.has_content
        rows.append({"resource": resource, "available": available, "accessible": can_access_resource(user, resource)})
    return rows


class AcademyHomeView(OrgPermissionRequiredMixin, TemplateView):
    permission_required = "academy.view"
    template_name = "academy/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["programs"] = Program.objects.filter(organization=self.request.organization).prefetch_related("courses")
        return context


# --- Acheteur ---------------------------------------------------------------

class OfferListView(OrgPermissionRequiredMixin, View):
    permission_required = "academy.view"

    def get(self, request):
        offers = list(services.purchasable_offers(request.organization).order_by("program__title_fr", "position"))
        for offer in offers:
            offer.open_order = services.open_order_for(request.user, offer)
            offer.has_access = services.paid_access_for(request.user, offer) is not None
        return render(request, "academy/offer_list.html", {"offers": offers})


class OfferDetailView(OrgPermissionRequiredMixin, View):
    permission_required = "academy.view"

    def get(self, request, pk):
        offer = get_object_or_404(services.purchasable_offers(request.organization), pk=pk)
        return render(request, "academy/offer_detail.html", self.context(request, offer, OrderForm()))

    @staticmethod
    def context(request, offer, form):
        return {
            "offer": offer,
            "resources": _included_resources(offer, request.user),
            "open_order": services.open_order_for(request.user, offer),
            "has_access": services.paid_access_for(request.user, offer) is not None,
            "can_buy": request_has_perm(request, "academy.buy"),
            "form": form,
        }


class OrderCreateView(OrgPermissionRequiredMixin, View):
    permission_required = "academy.buy"

    def post(self, request, pk):
        offer = get_object_or_404(services.purchasable_offers(request.organization), pk=pk)
        form = OrderForm(request.POST)
        if not form.is_valid():
            return render(request, "academy/offer_detail.html", OfferDetailView.context(request, offer, form), status=400)
        try:
            order, created = services.place_order(request=request, offer=offer)
        except (ValidationError, PermissionDenied) as exc:
            _report(request, exc)
            return redirect("academy:offer_detail", pk=offer.pk)
        if created:
            messages.success(request, _("Your order is recorded. No access is opened before the payment is confirmed."))
        else:
            messages.info(request, _("You already have an open order for this offer."))
        return redirect("academy:my_order_detail", pk=order.pk)


def _my_order(request, pk) -> Order:
    return get_object_or_404(
        Order.objects.select_related("offer", "offer__program"),
        pk=pk,
        organization=request.organization,
        user=request.user,
    )


class MyOrderListView(OrgPermissionRequiredMixin, View):
    permission_required = "academy.view"

    def get(self, request):
        orders = Order.objects.filter(organization=request.organization, user=request.user).select_related(
            "offer", "offer__program"
        )
        return render(request, "academy/my_order_list.html", {"orders": orders})


class MyOrderDetailView(OrgPermissionRequiredMixin, View):
    permission_required = "academy.view"

    def get(self, request, pk):
        order = _my_order(request, pk)
        enrollment = order.enrollments.first()
        return render(request, "academy/my_order_detail.html", {
            "order": order,
            "enrollment": enrollment,
            "has_access": enrollment is not None and enrollment.is_access_valid(),
            "resources": _included_resources(order.offer, request.user),
            "history": order.audit_log.select_related("actor"),
            "cancel_form": BuyerCancelForm(),
        })


class MyOrderCancelView(OrgPermissionRequiredMixin, View):
    permission_required = "academy.buy"

    def post(self, request, pk):
        order = _my_order(request, pk)
        form = BuyerCancelForm(request.POST)
        reason = form.cleaned_data["reason"] if form.is_valid() else ""
        try:
            services.cancel_order(request=request, order=order, reason=reason)
        except (ValidationError, PermissionDenied) as exc:
            _report(request, exc)
        else:
            messages.success(request, _("The order has been cancelled."))
        return redirect("academy:my_order_detail", pk=order.pk)


# --- Administration des commandes -------------------------------------------

def _org_order(request, pk) -> Order:
    return get_for_org(request, Order.objects.select_related("offer", "offer__program", "user"), pk=pk)


class OrderListView(OrgPermissionRequiredMixin, View):
    permission_required = "payments.view_orders"

    def get(self, request):
        form = OrderFilterForm(request.GET or None)
        orders = Order.objects.filter(organization=request.organization).select_related("offer", "offer__program", "user")
        status = ""
        if form.is_valid():
            status = form.cleaned_data["status"]
            if status:
                orders = orders.filter(status=status)
        to_verify = Order.objects.filter(
            organization=request.organization, status__in=(Order.Status.AWAITING_PAYMENT, Order.Status.PAYMENT_PENDING)
        ).count()
        page = Paginator(orders, 50).get_page(request.GET.get("page"))
        return render(request, "academy/order_list.html", {
            "page": page, "filter_form": form, "status": status, "to_verify": to_verify,
        })


class OrderDetailView(OrgPermissionRequiredMixin, View):
    permission_required = "payments.view_orders"

    def get(self, request, pk, forms=None):
        order = _org_order(request, pk)
        forms = forms or {}
        enrollment = order.enrollments.first()
        return render(request, "academy/order_detail.html", {
            "order": order,
            "enrollment": enrollment,
            "has_access": enrollment is not None and enrollment.is_access_valid(),
            "history": order.audit_log.select_related("actor"),
            "confirm_form": forms.get("confirm") or ConfirmPaymentForm(order=order),
            "cancel_form": forms.get("cancel") or AdminCancelForm(),
            "refund_form": forms.get("refund") or RefundForm(order=order),
            "can_confirm": request_has_perm(request, "payments.confirm_order"),
            "can_cancel": request_has_perm(request, "payments.cancel_order"),
            "can_refund": request_has_perm(request, "payments.refund_order"),
        }, status=400 if forms else 200)


class OrderConfirmView(OrgPermissionRequiredMixin, View):
    permission_required = "payments.confirm_order"

    def post(self, request, pk):
        order = _org_order(request, pk)
        form = ConfirmPaymentForm(request.POST, order=order)
        if not form.is_valid():
            return OrderDetailView().get(request, pk, forms={"confirm": form})
        try:
            order, confirmed = services.confirm_payment(
                request=request, order=order, note=form.cleaned_data["note"], reference=form.cleaned_data["reference"]
            )
        except (ValidationError, PermissionDenied) as exc:
            _report(request, exc)
        else:
            if confirmed:
                messages.success(request, _("Payment confirmed. Access to the offer is open."))
            else:
                messages.info(request, _("This order was already confirmed. Nothing was changed."))
        return redirect("academy:order_detail", pk=pk)


class OrderCancelView(OrgPermissionRequiredMixin, View):
    permission_required = "payments.cancel_order"

    def post(self, request, pk):
        order = _org_order(request, pk)
        form = AdminCancelForm(request.POST)
        if not form.is_valid():
            return OrderDetailView().get(request, pk, forms={"cancel": form})
        try:
            services.cancel_order(request=request, order=order, reason=form.cleaned_data["reason"])
        except (ValidationError, PermissionDenied) as exc:
            _report(request, exc)
        else:
            messages.success(request, _("The order has been cancelled."))
        return redirect("academy:order_detail", pk=pk)


class OrderRefundView(OrgPermissionRequiredMixin, View):
    permission_required = "payments.refund_order"

    def post(self, request, pk):
        order = _org_order(request, pk)
        form = RefundForm(request.POST, order=order)
        if not form.is_valid():
            return OrderDetailView().get(request, pk, forms={"refund": form})
        try:
            order = services.refund(
                request=request,
                order=order,
                amount=form.cleaned_data["amount"],
                reason=form.cleaned_data["reason"],
                reference=form.cleaned_data["reference"],
            )
        except (ValidationError, PermissionDenied) as exc:
            _report(request, exc)
        else:
            if order.status == Order.Status.REFUNDED:
                messages.success(request, _("Full refund recorded. Access has been removed."))
            else:
                messages.success(request, _("Partial refund recorded. Access is unchanged."))
        return redirect("academy:order_detail", pk=pk)
