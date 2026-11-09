"""Règles métier du module partners. Toutes les écritures passent par ici."""

from __future__ import annotations

import datetime as dt

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.core import audit
from apps.core.models import OrganizationSettings
from apps.core.permissions import has_full_affiliate_visibility

from .models import TRACK_FIELDS, Affiliate, FollowUp, Interaction, TrackEvent

AFFILIATE_FIELDS = [
    "display_name",
    "email",
    "phone",
    "country",
    "preferred_language",
    "status",
    "referral_link",
    "assigned_to",
]


def visible_affiliates(request) -> QuerySet[Affiliate]:
    """Affiliés visibles : toute l'organisation, ou seulement ceux attribués (conseiller)."""
    queryset = Affiliate.objects.filter(organization=request.organization)
    if not has_full_affiliate_visibility(request):
        queryset = queryset.filter(assigned_to=request.user)
    return queryset


def create_affiliate(*, organization, actor, data: dict) -> Affiliate:
    with transaction.atomic():
        affiliate = Affiliate(organization=organization, created_by=actor)
        for name in AFFILIATE_FIELDS:
            if name in data:
                setattr(affiliate, name, data[name])
        affiliate.full_clean()
        affiliate.save()
        audit.record("affiliate_created", actor=actor, organization=organization, target=affiliate, status=affiliate.status)
    return affiliate


def update_affiliate(*, affiliate: Affiliate, actor, data: dict) -> list[str]:
    changed = audit.changed_fields(affiliate, data, AFFILIATE_FIELDS)
    if not changed:
        return []
    with transaction.atomic():
        for name in changed:
            setattr(affiliate, name, data[name])
        affiliate.full_clean()
        affiliate.save()
        audit.record(
            "affiliate_updated", actor=actor, organization=affiliate.organization, target=affiliate, fields=changed
        )
    return changed


def set_archived(*, affiliate: Affiliate, actor, archived: bool) -> None:
    with transaction.atomic():
        affiliate.archived_at = timezone.now() if archived else None
        affiliate.archived_by = actor if archived else None
        affiliate.save(update_fields=["archived_at", "archived_by", "updated_at"])
        audit.record(
            "affiliate_archived" if archived else "affiliate_restored",
            actor=actor,
            organization=affiliate.organization,
            target=affiliate,
        )


def record_track(*, affiliate: Affiliate, actor, track: str, value: str, declared_on: dt.date, source: str, note: str = "") -> TrackEvent:
    """Enregistre une étape déclarée du parcours et met à jour l'état courant."""
    if track not in TRACK_FIELDS:
        raise ValidationError(_("Unknown step."))
    status_field, date_field, choices = TRACK_FIELDS[track]
    if value not in choices.values:
        raise ValidationError(_("This status is not valid for this step."))
    if declared_on > timezone.localdate():
        raise ValidationError(_("The date cannot be in the future."))
    with transaction.atomic():
        locked = Affiliate.objects.select_for_update().get(pk=affiliate.pk)
        previous = getattr(locked, status_field)
        event = TrackEvent.objects.create(
            organization=locked.organization,
            affiliate=locked,
            track=track,
            value=value,
            previous_value=previous,
            declared_on=declared_on,
            source=source,
            note=note,
            recorded_by=actor,
        )
        setattr(locked, status_field, value)
        setattr(locked, date_field, declared_on)
        locked.save(update_fields=[status_field, date_field, "updated_at"])
        audit.record(
            "affiliate_track_recorded",
            actor=actor,
            organization=locked.organization,
            target=locked,
            track=track,
            previous=previous,
            value=value,
            source=source,
        )
    setattr(affiliate, status_field, value)
    setattr(affiliate, date_field, declared_on)
    return event


def add_interaction(*, affiliate: Affiliate, actor, kind: str, occurred_at, summary: str) -> Interaction:
    if occurred_at > timezone.now() + dt.timedelta(minutes=5):
        raise ValidationError(_("The date cannot be in the future."))
    with transaction.atomic():
        interaction = Interaction.objects.create(
            organization=affiliate.organization,
            affiliate=affiliate,
            kind=kind,
            occurred_at=occurred_at,
            summary=summary,
            author=actor,
        )
        if interaction.counts_as_contact:
            Affiliate.objects.filter(pk=affiliate.pk).filter(
                Q(last_contact_at__isnull=True) | Q(last_contact_at__lt=occurred_at)
            ).update(last_contact_at=occurred_at)
        audit.record("interaction_added", actor=actor, organization=affiliate.organization, target=affiliate, kind=kind)
    affiliate.refresh_from_db(fields=["last_contact_at"])
    return interaction


def create_followup(*, affiliate: Affiliate, actor, title: str, due_on: dt.date, assigned_to=None, note: str = "") -> FollowUp:
    with transaction.atomic():
        followup = FollowUp.objects.create(
            organization=affiliate.organization,
            affiliate=affiliate,
            title=title,
            due_on=due_on,
            assigned_to=assigned_to,
            note=note,
            created_by=actor,
        )
        audit.record("followup_created", actor=actor, organization=affiliate.organization, target=followup, due_on=due_on)
    return followup


def close_followup(*, followup: FollowUp, actor, status: str) -> None:
    if status not in (FollowUp.Status.DONE, FollowUp.Status.CANCELLED):
        raise ValidationError(_("Unknown status."))
    if followup.status != FollowUp.Status.OPEN:
        raise ValidationError(_("This follow-up is already closed."))
    with transaction.atomic():
        followup.status = status
        followup.closed_at = timezone.now()
        followup.closed_by = actor
        followup.save(update_fields=["status", "closed_at", "closed_by"])
        audit.record("followup_closed", actor=actor, organization=followup.organization, target=followup, status=status)


# --- Alertes -----------------------------------------------------------------

def _active(queryset):
    return queryset.filter(archived_at__isnull=True).exclude(status=Affiliate.Status.INACTIVE)


def contact_stale(queryset, settings_obj: OrganizationSettings):
    limit = timezone.now() - dt.timedelta(days=settings_obj.contact_stale_days)
    return _active(queryset).filter(
        Q(last_contact_at__lt=limit) | Q(last_contact_at__isnull=True, created_at__lt=limit)
    )


def registration_pending(queryset):
    return _active(queryset).exclude(registration_status=Affiliate.Registration.ACCOUNT_CREATED)


def verification_pending(queryset):
    return _active(queryset).filter(registration_status=Affiliate.Registration.ACCOUNT_CREATED).exclude(
        verification_status__in=Affiliate.VERIFICATION_FINAL
    )


def registration_stuck(queryset, settings_obj: OrganizationSettings):
    limit = timezone.localdate() - dt.timedelta(days=settings_obj.registration_stuck_days)
    limit_dt = timezone.now() - dt.timedelta(days=settings_obj.registration_stuck_days)
    return registration_pending(queryset).filter(
        Q(registration_updated_on__lt=limit) | Q(registration_updated_on__isnull=True, created_at__lt=limit_dt)
    )


def verification_stuck(queryset, settings_obj: OrganizationSettings):
    limit = timezone.localdate() - dt.timedelta(days=settings_obj.verification_stuck_days)
    return verification_pending(queryset).filter(
        Q(verification_updated_on__lt=limit)
        | Q(verification_updated_on__isnull=True, registration_updated_on__lt=limit)
    )


ALERTS = {
    "contact_stale": contact_stale,
    "registration_stuck": registration_stuck,
    "verification_stuck": verification_stuck,
}


def open_followups(request) -> QuerySet[FollowUp]:
    queryset = FollowUp.objects.filter(
        organization=request.organization, status=FollowUp.Status.OPEN, affiliate__archived_at__isnull=True
    )
    if not has_full_affiliate_visibility(request):
        queryset = queryset.filter(affiliate__assigned_to=request.user)
    return queryset
