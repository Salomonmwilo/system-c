"""Commandes d'Academy : création, confirmation manuelle, annulation, remboursement.

Toutes les écritures passent par ces fonctions. Aucun prestataire de paiement
n'est connecté : une commande n'est payée que lorsqu'une personne autorisée
(permission ``payments.confirm_order``) confirme la réception, avec une note.

Remboursements :
- intégral : le total remboursé atteint le prix payé. La commande passe à
  « remboursée », l'inscription est annulée (jamais supprimée), la progression
  est conservée, et l'accès est retiré immédiatement ;
- partiel : le montant est enregistré, la commande reste « payée » et les droits
  ne changent pas. Aucune règle commerciale n'est appliquée automatiquement ;
  la page de la commande le signale. Retirer l'accès ensuite est une action
  distincte (``revoke_access``), autorisée, motivée et auditée.

Le cumul des remboursements ne dépasse jamais le montant payé (service,
formulaire, contrainte et déclencheur en base).

Personne ne confirme le paiement de sa propre commande. Seule exception : les
programmes de démonstration (« [Démo] »), et seulement quand DEBUG est actif.
Hors DEBUG, les offres de démonstration ne sont ni visibles ni commandables, et
leurs commandes ne peuvent pas être confirmées.

Durée d'accès : celle de l'offre au moment de la confirmation. Par défaut, sans
date d'expiration ; l'accès porte sur le contenu de l'offre achetée.

PostgreSQL vérifie aussi les transitions, l'historique et les montants
(migration 0008).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.core import audit
from apps.core.permissions import request_has_perm

from .models import Enrollment, Order, OrderAudit, ProgramOffer

S = Order.Status


def purchasable_offers(organization):
    """Offres publiées d'un programme publié : les seules qu'on peut commander.

    Les offres de démonstration n'en font partie que si DEBUG est actif.
    """
    offers = ProgramOffer.objects.filter(
        program__organization=organization,
        program__is_published=True,
        status=ProgramOffer.Status.PUBLISHED,
    ).select_related("program")
    if not settings.DEBUG:
        offers = offers.filter(program__is_demo=False)
    return offers


def is_demo_order(order: Order) -> bool:
    return order.offer.program.is_demo


def self_confirmation_allowed(order: Order) -> bool:
    """Confirmer sa propre commande : seulement une commande de démonstration, en DEBUG."""
    return settings.DEBUG and is_demo_order(order)


def open_order_for(user, offer) -> Order | None:
    return Order.objects.filter(user=user, offer=offer, status__in=Order.OPEN_STATUSES).first()


def paid_access_for(user, offer) -> Enrollment | None:
    for enrollment in Enrollment.objects.filter(user=user, offer=offer, status=Enrollment.Status.ACTIVE).select_related("order"):
        if enrollment.is_access_valid():
            return enrollment
    return None


def _require(request, perm: str) -> None:
    if not request_has_perm(request, perm):
        raise PermissionDenied


def _same_organization(request, order: Order) -> None:
    if order.organization_id != getattr(request.organization, "pk", None):
        raise PermissionDenied


def _lock(order: Order) -> Order:
    return Order.objects.select_for_update().get(pk=order.pk)


def _clean_text(value: str, limit: int) -> str:
    return (value or "").strip()[:limit]


# --- Acheteur ---------------------------------------------------------------

def place_order(*, request, offer: ProgramOffer) -> tuple[Order, bool]:
    """Crée une commande en attente de paiement ; renvoie (commande, créée).

    Une commande encore ouverte pour la même offre est réutilisée : pas de doublon.
    """
    _require(request, "academy.buy")
    if not purchasable_offers(request.organization).filter(pk=offer.pk).exists():
        raise ValidationError(_("This offer is not available."))
    user = request.user
    with transaction.atomic():
        # Verrou sur l'offre : deux envois simultanés ne créent pas deux commandes.
        ProgramOffer.objects.select_for_update().get(pk=offer.pk)
        existing = open_order_for(user, offer)
        if existing is not None:
            return existing, False
        if paid_access_for(user, offer) is not None:
            raise ValidationError(_("You already have access to this offer."))
        order = Order.objects.create(
            organization=request.organization,
            user=user,
            offer=offer,
            status=S.AWAITING_PAYMENT,
            risk_notice_version=settings.SYSTEMC_RISK_NOTICE_VERSION,
            terms_version=settings.SYSTEMC_TERMS_VERSION,
        )
        OrderAudit.objects.create(
            order=order,
            action=OrderAudit.Action.CREATED,
            new_status=S.AWAITING_PAYMENT,
            actor=user,
            amount=order.price,
            currency=order.currency,
        )
        audit.record(
            "academy_order_created",
            actor=user,
            organization=request.organization,
            target=order,
            offer=offer.slug,
            amount=order.price,
            currency=order.currency,
        )
    return order, True


# --- Administration ---------------------------------------------------------

def confirm_payment(*, request, order: Order, note: str, reference: str = "") -> tuple[Order, bool]:
    """Confirme la réception du paiement et ouvre les droits ; renvoie (commande, confirmée maintenant).

    Une deuxième confirmation ne crée ni historique ni inscription supplémentaire.
    """
    _require(request, "payments.confirm_order")
    _same_organization(request, order)
    if is_demo_order(order) and not settings.DEBUG:
        raise ValidationError(_("A demonstration order can only be confirmed in a local test environment."))
    if order.user_id == request.user.pk and not self_confirmation_allowed(order):
        raise ValidationError(_("You cannot confirm the payment of your own order. Another authorised person must do it."))
    note = _clean_text(note, 500)
    reference = _clean_text(reference, 100)
    if not note:
        raise ValidationError(_("A verification note is required."))
    with transaction.atomic():
        locked = _lock(order)
        if locked.status == S.PAID:
            return locked, False
        if locked.status not in (S.AWAITING_PAYMENT, S.PAYMENT_PENDING):
            raise ValidationError(_("This order can no longer be confirmed."))
        previous = locked.status
        OrderAudit.objects.create(
            order=locked,
            action=OrderAudit.Action.PAYMENT_VERIFIED,
            old_status=previous,
            new_status=S.PAID,
            actor=request.user,
            reference=reference,
            notes=note,
            amount=locked.price,
            currency=locked.currency,
        )
        locked.status = S.PAID
        update = ["status", "updated_at"]
        if reference:
            locked.transaction_ref = reference
            update.append("transaction_ref")
        locked.save(update_fields=update)
        Enrollment.objects.get_or_create(
            order=locked,
            defaults={
                "organization": locked.organization,
                "program": locked.offer.program,
                "user": locked.user,
                "offer": locked.offer,
                "status": Enrollment.Status.ACTIVE,
                "access_mode": locked.offer.access_mode,
                "access_until": locked.offer.access_until_from(timezone.now()),
            },
        )
        audit.record(
            "academy_payment_confirmed",
            actor=request.user,
            organization=locked.organization,
            target=locked,
            previous_status=previous,
            amount=locked.price,
            currency=locked.currency,
            reference=reference,
        )
    return locked, True


def cancel_order(*, request, order: Order, reason: str = "") -> Order:
    """Annule une commande non payée : par son acheteur, ou avec ``payments.cancel_order``."""
    is_buyer = order.user_id == request.user.pk and request_has_perm(request, "academy.buy")
    is_admin = request_has_perm(request, "payments.cancel_order")
    if not (is_buyer or is_admin):
        raise PermissionDenied
    _same_organization(request, order)
    reason = _clean_text(reason, 500)
    if not is_buyer and not reason:
        raise ValidationError(_("A reason is required."))
    with transaction.atomic():
        locked = _lock(order)
        if locked.status == S.CANCELLED:
            return locked
        if not locked.is_open:
            raise ValidationError(_("Only an unpaid order can be cancelled. A paid order is refunded."))
        previous = locked.status
        OrderAudit.objects.create(
            order=locked,
            action=OrderAudit.Action.CANCELLED,
            old_status=previous,
            new_status=S.CANCELLED,
            actor=request.user,
            notes=reason or _("Cancelled by the buyer."),
        )
        locked.status = S.CANCELLED
        locked.save(update_fields=["status", "updated_at"])
        audit.record(
            "academy_order_cancelled",
            actor=request.user,
            organization=locked.organization,
            target=locked,
            previous_status=previous,
            by_buyer=is_buyer and not is_admin,
        )
    return locked


def refund(*, request, order: Order, amount, reason: str, reference: str = "") -> Order:
    """Enregistre un remboursement. Intégral : droits retirés. Partiel : droits inchangés."""
    _require(request, "payments.refund_order")
    _same_organization(request, order)
    reason = _clean_text(reason, 500)
    reference = _clean_text(reference, 100)
    if not reason:
        raise ValidationError(_("A justification is required."))
    try:
        amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(_("Enter a valid amount.")) from exc
    with transaction.atomic():
        locked = _lock(order)
        if locked.status != S.PAID:
            raise ValidationError(_("Only a paid order can be refunded."))
        remaining = locked.remaining_refundable
        if amount <= 0 or amount > remaining:
            raise ValidationError(
                _("The amount must be greater than zero and at most %(remaining)s %(currency)s.")
                % {"remaining": remaining, "currency": locked.currency}
            )
        full = amount == remaining
        new_status = S.REFUNDED if full else S.PAID
        OrderAudit.objects.create(
            order=locked,
            action=OrderAudit.Action.REFUNDED if full else OrderAudit.Action.PARTIAL_REFUND,
            old_status=S.PAID,
            new_status=new_status,
            actor=request.user,
            reference=reference,
            notes=reason,
            amount=amount,
            currency=locked.currency,
        )
        locked.refunded_amount += amount
        locked.status = new_status
        locked.save(update_fields=["refunded_amount", "status", "updated_at"])
        if full:
            # Accès retiré immédiatement ; l'inscription et la progression restent.
            for enrollment in Enrollment.objects.filter(order=locked).exclude(status=Enrollment.Status.CANCELLED):
                enrollment.status = Enrollment.Status.CANCELLED
                enrollment.save(update_fields=["status"])
        audit.record(
            "academy_order_refunded" if full else "academy_order_partially_refunded",
            actor=request.user,
            organization=locked.organization,
            target=locked,
            amount=amount,
            currency=locked.currency,
            refunded_total=locked.refunded_amount,
            reference=reference,
        )
    return locked


def revoke_access(*, request, order: Order, reason: str) -> Enrollment:
    """Retire l'accès après un remboursement partiel : action distincte, motivée et auditée.

    La commande reste « payée » et son historique est conservé ; l'inscription
    passe à « accès révoqué » et ne peut plus redevenir active.
    """
    _require(request, "payments.revoke_access")
    _same_organization(request, order)
    reason = _clean_text(reason, 500)
    if not reason:
        raise ValidationError(_("A reason is required."))
    with transaction.atomic():
        locked = _lock(order)
        if not locked.has_partial_refund:
            raise ValidationError(_("Access can only be revoked here after a partial refund of a paid order."))
        enrollment = Enrollment.objects.select_for_update().filter(order=locked).first()
        if enrollment is None:
            raise ValidationError(_("This order has no enrolment."))
        if enrollment.status == Enrollment.Status.REVOKED:
            return enrollment
        OrderAudit.objects.create(
            order=locked,
            action=OrderAudit.Action.ACCESS_REVOKED,
            old_status=locked.status,
            new_status=locked.status,
            actor=request.user,
            notes=reason,
        )
        previous = enrollment.status
        enrollment.status = Enrollment.Status.REVOKED
        enrollment.save(update_fields=["status"])
        audit.record(
            "academy_access_revoked",
            actor=request.user,
            organization=locked.organization,
            target=locked,
            enrollment_status=previous,
            refunded_total=locked.refunded_amount,
        )
    return enrollment
