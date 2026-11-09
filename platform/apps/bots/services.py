"""Règles métier du CRM bots. Toutes les écritures passent par ces fonctions.

Rappel : rien ici ne communique avec le VPS ni avec Deriv. Chaque action est une
déclaration administrative enregistrée et journalisée.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.core import audit
from apps.core.models import OrganizationSettings
from apps.core.permissions import request_has_perm
from apps.core.templatetags.systemc import plain_decimal

from .models import (
    PARAMETER_KEYS,
    AccountType,
    ApplicationDeclaration,
    BotStatus,
    BotUser,
    ConfigurationVersion,
    Override,
    ParameterDefinition,
    ParameterValue,
    RobotType,
    StatusEvent,
)

REAL_CONFIRMATION_WORDING = gettext_lazy(
    "I confirm that this configuration concerns a REAL Deriv account. This is an administrative "
    "declaration only: no command is sent to the VPS or to Deriv."
)


# --- Catalogue de paramètres ------------------------------------------------

def ensure_parameter_catalog(organization) -> None:
    """Crée les définitions manquantes : les 12 clés pour chaque type de robot.

    Hypothèse par défaut documentée : chaque clé est « utilisée » mais « à vérifier ».
    Aucune valeur n'est obligatoire ; l'administrateur désactive les clés inutiles.
    """
    existing = set(
        ParameterDefinition.objects.filter(organization=organization).values_list("robot_type", "key")
    )
    missing = [
        ParameterDefinition(organization=organization, robot_type=robot, key=key)
        for robot in RobotType.values
        for key in PARAMETER_KEYS
        if (robot, key) not in existing
    ]
    if missing:
        ParameterDefinition.objects.bulk_create(missing)


def definitions_for(organization, robot_type: str):
    ensure_parameter_catalog(organization)
    return ParameterDefinition.objects.filter(organization=organization, robot_type=robot_type, enabled=True).order_by("key")


# --- Calcul du statut -------------------------------------------------------

def effective_applied(bot_user: BotUser):
    """Déclarations « appliquée » qui n'ont pas été corrigées."""
    corrected = ApplicationDeclaration.objects.filter(
        version__bot_user=bot_user, kind=ApplicationDeclaration.Kind.CORRECTION
    ).values("corrects_id")
    return ApplicationDeclaration.objects.filter(
        version__bot_user=bot_user, kind=ApplicationDeclaration.Kind.APPLIED
    ).exclude(id__in=corrected)


def compute_status(bot_user: BotUser) -> dict:
    latest = bot_user.versions.filter(state=ConfigurationVersion.State.VALIDATED).order_by("-number").first()
    applied = effective_applied(bot_user)
    latest_applied = latest is not None and applied.filter(version=latest).exists()
    older_applied = latest is not None and applied.filter(version__number__lt=latest.number).exists()
    if bot_user.override == Override.DISABLED:
        status = BotStatus.DISABLED
    elif bot_user.override == Override.PAUSED:
        status = BotStatus.PAUSED
    elif latest is None:
        status = BotStatus.TO_CONFIGURE
    elif latest_applied:
        status = BotStatus.APPLIED
    elif older_applied:
        status = BotStatus.MODIFICATION_REQUESTED
    else:
        status = BotStatus.TO_CONFIGURE
    return {
        "status": status,
        "current_account_type": latest.account_type if latest else "",
        "pending_since": latest.validated_at if latest is not None and not latest_applied else None,
        "last_applied_on": applied.aggregate(last=Max("applied_on"))["last"],
    }


def recompute_status(bot_user: BotUser) -> BotUser:
    values = compute_status(bot_user)
    changed = [name for name, value in values.items() if getattr(bot_user, name) != value]
    for name, value in values.items():
        setattr(bot_user, name, value)
    if changed:
        bot_user.save(update_fields=changed + ["updated_at"])
    return bot_user


# --- Fiches robot -----------------------------------------------------------

BOT_USER_FIELDS = ["wants_bot", "robot_type", "vps_label", "admin_note"]


def create_bot_user(*, organization, affiliate, actor, data: dict) -> BotUser:
    if affiliate.organization_id != organization.pk:
        raise PermissionDenied
    if affiliate.archived_at is not None:
        raise ValidationError(_("This affiliate is archived."))
    if BotUser.objects.filter(affiliate=affiliate).exists():
        raise ValidationError(_("This affiliate already has a robot record."))
    with transaction.atomic():
        bot_user = BotUser(organization=organization, affiliate=affiliate, created_by=actor)
        for name in BOT_USER_FIELDS:
            if name in data:
                setattr(bot_user, name, data[name])
        bot_user.full_clean()
        bot_user.save()
        ensure_parameter_catalog(organization)
        audit.record(
            "bot_user_created",
            actor=actor,
            organization=organization,
            target=bot_user,
            affiliate_id=affiliate.pk,
            robot_type=bot_user.robot_type,
            wants_bot=bot_user.wants_bot,
        )
    return bot_user


def update_bot_user(*, bot_user: BotUser, actor, data: dict) -> list[str]:
    changed = audit.changed_fields(bot_user, data, BOT_USER_FIELDS)
    if not changed:
        return []
    with transaction.atomic():
        for name in changed:
            setattr(bot_user, name, data[name])
        bot_user.full_clean()
        bot_user.save()
        audit.record(
            "bot_user_updated",
            actor=actor,
            organization=bot_user.organization,
            target=bot_user,
            fields=changed,
            robot_type=bot_user.robot_type,
        )
    return changed


# --- Versions de configuration ----------------------------------------------

def _lock(bot_user: BotUser) -> BotUser:
    return BotUser.objects.select_for_update().get(pk=bot_user.pk)


def latest_validated(bot_user: BotUser):
    return bot_user.versions.filter(state=ConfigurationVersion.State.VALIDATED).order_by("-number").first()


def current_draft(bot_user: BotUser):
    return bot_user.versions.filter(state=ConfigurationVersion.State.DRAFT).first()


def start_version(*, request, bot_user: BotUser) -> ConfigurationVersion:
    """Ouvre un brouillon (ou renvoie celui qui existe), copié de la dernière version validée."""
    actor = request.user
    with transaction.atomic():
        locked = _lock(bot_user)
        draft = current_draft(locked)
        if draft is not None:
            return draft
        if locked.override == Override.DISABLED:
            raise ValidationError(_("This robot record is disabled. Reactivate it before preparing a configuration."))
        if not locked.robot_type:
            raise ValidationError(_("Choose a robot type before preparing a configuration."))
        base = latest_validated(locked)
        account_type = base.account_type if base else AccountType.DEMO
        if account_type == AccountType.REAL and not request_has_perm(request, "bots.manage_real"):
            raise PermissionDenied(_("Only a CRM administrator can prepare a configuration for a real account."))
        number = (locked.versions.aggregate(n=Max("number"))["n"] or 0) + 1
        settings_obj = OrganizationSettings.for_organization(locked.organization)
        draft = ConfigurationVersion.objects.create(
            organization=locked.organization,
            bot_user=locked,
            number=number,
            robot_type=locked.robot_type,
            account_type=account_type,
            reference_capital=base.reference_capital if base else None,
            currency=base.currency if base else settings_obj.default_currency,
            created_by=actor,
        )
        if base is not None and base.robot_type == locked.robot_type:
            allowed = set(definitions_for(locked.organization, locked.robot_type).values_list("key", flat=True))
            ParameterValue.objects.bulk_create(
                [
                    ParameterValue(version=draft, key=p.key, value=p.value, unit=p.unit)
                    for p in base.parameters.all()
                    if p.key in allowed
                ]
            )
        audit.record(
            "version_drafted",
            actor=actor,
            organization=locked.organization,
            target=draft,
            bot_user_id=locked.pk,
            number=number,
            copied_from=base.number if base else None,
        )
    return draft


def _check_draft_access(request, version: ConfigurationVersion) -> None:
    if version.state != ConfigurationVersion.State.DRAFT:
        raise ValidationError(_("A validated version cannot be changed. Create a new version."))
    if version.account_type == AccountType.REAL and not request_has_perm(request, "bots.manage_real"):
        raise PermissionDenied(_("Only a CRM administrator can change a configuration for a real account."))


def validate_parameter_values(organization, robot_type: str, values: dict[str, Decimal | None]) -> dict[str, Decimal]:
    """Contrôle les valeurs : clé autorisée pour ce robot, type numérique, bornes."""
    definitions = {d.key: d for d in definitions_for(organization, robot_type)}
    clean: dict[str, Decimal] = {}
    errors = []
    for key, value in values.items():
        if value is None:
            continue
        if key not in definitions:
            errors.append(_("%(key)s is not an allowed parameter for this robot.") % {"key": key})
            continue
        definition = definitions[key]
        if definition.min_value is not None and value < definition.min_value:
            errors.append(_("%(key)s must be at least %(min)s.") % {"key": key, "min": plain_decimal(definition.min_value)})
        if definition.max_value is not None and value > definition.max_value:
            errors.append(_("%(key)s must be at most %(max)s.") % {"key": key, "max": plain_decimal(definition.max_value)})
        clean[key] = value
    if errors:
        raise ValidationError(errors)
    return clean


def update_draft(*, request, version: ConfigurationVersion, data: dict, parameters: dict) -> None:
    actor = request.user
    with transaction.atomic():
        version = ConfigurationVersion.objects.select_for_update().get(pk=version.pk)
        _check_draft_access(request, version)
        new_account_type = data.get("account_type", version.account_type)
        if new_account_type == AccountType.REAL and not request_has_perm(request, "bots.manage_real"):
            raise PermissionDenied(_("Only a CRM administrator can declare a real account."))
        clean_params = validate_parameter_values(version.organization, version.robot_type, parameters)
        fields = ["account_type", "reference_capital", "currency", "admin_note"]
        changed = [name for name in fields if name in data and getattr(version, name) != data[name]]
        for name in fields:
            if name in data:
                setattr(version, name, data[name])
        version.full_clean()
        version.save()
        previous = {p.key: p.value for p in version.parameters.all()}
        units = {d.key: d.unit for d in definitions_for(version.organization, version.robot_type)}
        version.parameters.all().delete()
        ParameterValue.objects.bulk_create(
            [ParameterValue(version=version, key=k, value=v, unit=units.get(k, "")) for k, v in clean_params.items()]
        )
        changed_params = sorted(k for k in set(previous) | set(clean_params) if previous.get(k) != clean_params.get(k))
        audit.record(
            "version_draft_updated",
            actor=actor,
            organization=version.organization,
            target=version,
            fields=changed,
            parameters_changed=changed_params,
            account_type=version.account_type,
            reference_capital=version.reference_capital,
        )


def delete_draft(*, request, version: ConfigurationVersion) -> None:
    with transaction.atomic():
        version = ConfigurationVersion.objects.select_for_update().get(pk=version.pk)
        _check_draft_access(request, version)
        audit.record(
            "version_draft_deleted",
            actor=request.user,
            organization=version.organization,
            target=version,
            number=version.number,
        )
        version.delete()


def validate_version(*, request, version: ConfigurationVersion, real_declaration: dict | None = None) -> ConfigurationVersion:
    """Valide un brouillon. La version devient immuable.

    Pour un compte réel : crm_admin uniquement, confirmation explicite, date et
    note obligatoires, et trace d'audit dédiée.
    """
    actor = request.user
    if not request_has_perm(request, "bots.validate_version"):
        raise PermissionDenied
    with transaction.atomic():
        bot_user = _lock(version.bot_user)
        version = ConfigurationVersion.objects.select_for_update().get(pk=version.pk)
        if version.state != ConfigurationVersion.State.DRAFT:
            raise ValidationError(_("This version has already been validated."))
        if bot_user.override == Override.DISABLED:
            raise ValidationError(_("This robot record is disabled. Reactivate it before validating a configuration."))
        if version.reference_capital is None:
            raise ValidationError(_("Enter the reference capital before validating."))
        now = timezone.now()
        if version.account_type == AccountType.REAL:
            if not request_has_perm(request, "bots.manage_real"):
                raise PermissionDenied(_("Only a CRM administrator can declare a real account."))
            declaration = real_declaration or {}
            if not declaration.get("confirmed"):
                raise ValidationError(_("Explicit confirmation is required for a real account."))
            declared_on = declaration.get("declared_on")
            note = (declaration.get("note") or "").strip()
            if not declared_on or not note:
                raise ValidationError(_("A date and a note are required to declare a real account."))
            if declared_on > timezone.localdate():
                raise ValidationError(_("The date cannot be in the future."))
            version.real_confirmed_at = now
            version.real_confirmed_by = actor
            version.real_declared_on = declared_on
            version.real_declaration_note = note[:500]
            version.real_confirmation_wording = str(REAL_CONFIRMATION_WORDING)[:300]
        version.state = ConfigurationVersion.State.VALIDATED
        version.validated_at = now
        version.validated_by = actor
        version.save()
        if version.account_type == AccountType.REAL:
            audit.record(
                "real_account_declared",
                actor=actor,
                organization=version.organization,
                target=version,
                bot_user_id=bot_user.pk,
                number=version.number,
                declared_on=version.real_declared_on,
            )
        audit.record(
            "version_validated",
            actor=actor,
            organization=version.organization,
            target=version,
            bot_user_id=bot_user.pk,
            number=version.number,
            account_type=version.account_type,
            reference_capital=version.reference_capital,
            parameters=sorted(version.parameters.values_list("key", flat=True)),
        )
        recompute_status(bot_user)
    return version


# --- Déclarations d'application ---------------------------------------------

def declare_applied(*, request, version: ConfigurationVersion, applied_on: dt.date, note: str = "") -> ApplicationDeclaration:
    actor = request.user
    if not request_has_perm(request, "bots.declare_applied"):
        raise PermissionDenied
    with transaction.atomic():
        bot_user = _lock(version.bot_user)
        version = ConfigurationVersion.objects.get(pk=version.pk)
        if version.state != ConfigurationVersion.State.VALIDATED:
            raise ValidationError(_("Only a validated version can be declared applied."))
        if version.account_type == AccountType.REAL and not request_has_perm(request, "bots.manage_real"):
            raise PermissionDenied(_("Only a CRM administrator can declare a real-account configuration applied."))
        latest = latest_validated(bot_user)
        if latest is None or latest.pk != version.pk:
            raise ValidationError(_("Only the latest validated version can be declared applied."))
        if effective_applied(bot_user).filter(version=version).exists():
            raise ValidationError(_("This version is already declared applied."))
        if applied_on > timezone.localdate():
            raise ValidationError(_("The date cannot be in the future."))
        declaration = ApplicationDeclaration.objects.create(
            organization=version.organization,
            version=version,
            kind=ApplicationDeclaration.Kind.APPLIED,
            applied_on=applied_on,
            note=note[:500],
            recorded_by=actor,
        )
        recompute_status(bot_user)
        audit.record(
            "configuration_declared_applied",
            actor=actor,
            organization=version.organization,
            target=declaration,
            bot_user_id=bot_user.pk,
            number=version.number,
            applied_on=applied_on,
            account_type=version.account_type,
        )
    return declaration


def correct_declaration(*, request, declaration: ApplicationDeclaration, reason: str) -> ApplicationDeclaration:
    actor = request.user
    if not request_has_perm(request, "bots.correct_declaration"):
        raise PermissionDenied
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError(_("A reason is required to correct a declaration."))
    with transaction.atomic():
        bot_user = _lock(declaration.version.bot_user)
        declaration = ApplicationDeclaration.objects.select_related("version").get(pk=declaration.pk)
        if declaration.kind != ApplicationDeclaration.Kind.APPLIED:
            raise ValidationError(_("Only an application declaration can be corrected."))
        if ApplicationDeclaration.objects.filter(corrects=declaration).exists():
            raise ValidationError(_("This declaration has already been corrected."))
        if declaration.version.account_type == AccountType.REAL and not request_has_perm(request, "bots.manage_real"):
            raise PermissionDenied(_("Only a CRM administrator can correct a real-account declaration."))
        correction = ApplicationDeclaration.objects.create(
            organization=declaration.organization,
            version=declaration.version,
            kind=ApplicationDeclaration.Kind.CORRECTION,
            corrects=declaration,
            note=reason[:500],
            recorded_by=actor,
        )
        recompute_status(bot_user)
        audit.record(
            "declaration_corrected",
            actor=actor,
            organization=declaration.organization,
            target=correction,
            bot_user_id=bot_user.pk,
            corrected_id=declaration.pk,
        )
    return correction


# --- Pause, désactivation, réactivation -------------------------------------

def set_override(*, request, bot_user: BotUser, override: str, reason: str) -> BotUser:
    actor = request.user
    reason = (reason or "").strip()
    if override not in Override.values:
        raise ValidationError(_("Unknown status."))
    needed = "bots.pause" if override == Override.PAUSED else "bots.disable"
    if not request_has_perm(request, needed):
        raise PermissionDenied
    if not reason:
        raise ValidationError(_("A reason is required."))
    with transaction.atomic():
        locked = _lock(bot_user)
        if locked.override == override:
            raise ValidationError(_("This status is already set."))
        if override == Override.PAUSED and locked.override == Override.DISABLED:
            raise ValidationError(_("A disabled record must be reactivated before being paused."))
        previous = locked.override
        StatusEvent.objects.create(
            organization=locked.organization,
            bot_user=locked,
            from_override=previous,
            to_override=override,
            reason=reason[:300],
            actor=actor,
        )
        locked.override = override
        locked.override_reason = "" if override == Override.NONE else reason[:300]
        locked.override_at = timezone.now()
        locked.override_by = actor
        locked.save(update_fields=["override", "override_reason", "override_at", "override_by", "updated_at"])
        recompute_status(locked)
        audit.record(
            "bot_user_status_changed",
            actor=actor,
            organization=locked.organization,
            target=locked,
            previous=previous,
            override=override,
        )
    return locked


# --- Alertes ----------------------------------------------------------------

def modification_pending(queryset, settings_obj: OrganizationSettings):
    limit = timezone.now() - dt.timedelta(days=settings_obj.modification_pending_days)
    return queryset.filter(status=BotStatus.MODIFICATION_REQUESTED, pending_since__lt=limit)


def configuration_review_due(queryset, settings_obj: OrganizationSettings):
    limit = timezone.localdate() - dt.timedelta(days=settings_obj.configuration_review_days)
    return queryset.filter(status=BotStatus.APPLIED, last_applied_on__lt=limit)


def to_apply(queryset):
    return queryset.filter(status=BotStatus.TO_CONFIGURE, wants_bot=True)


ALERTS = {
    "modification_pending": modification_pending,
    "configuration_review": configuration_review_due,
}
