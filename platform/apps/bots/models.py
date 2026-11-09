"""Module bots : CRM administratif des utilisateurs de robots.

Ce module ne communique avec aucun robot ni avec le VPS. Il enregistre ce que
l'administrateur déclare. Aucun champ n'est destiné à un secret (token Deriv,
mot de passe, clé API) : les paramètres viennent d'une liste blanche fermée et
leurs valeurs sont uniquement numériques.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import AppendOnlyModel, Organization


class RobotType(models.TextChoices):
    DIFFERS = "DIFFERS", "DIFFERS"
    OVER_UNDER = "OVER_UNDER", "OVER/UNDER"


class AccountType(models.TextChoices):
    DEMO = "demo", _("Demo")
    REAL = "real", _("Real")


class ParameterKey(models.TextChoices):
    """Liste blanche fermée des paramètres non secrets (inventaire validé)."""

    STAKE = "STAKE", "STAKE"
    DURATION = "DURATION", "DURATION"
    INTERVAL = "INTERVAL", "INTERVAL"
    MAX_TRADES = "MAX_TRADES", "MAX_TRADES"
    MAX_TRADES_DAY = "MAX_TRADES_DAY", "MAX_TRADES_DAY"
    SESSION_TARGET = "SESSION_TARGET", "SESSION_TARGET"
    SESSION_PAUSE = "SESSION_PAUSE", "SESSION_PAUSE"
    DAILY_TARGET = "DAILY_TARGET", "DAILY_TARGET"
    DAILY_MAX_LOSS = "DAILY_MAX_LOSS", "DAILY_MAX_LOSS"
    DAILY_MAX_LOSS_DEMO = "DAILY_MAX_LOSS_DEMO", "DAILY_MAX_LOSS_DEMO"
    CAPITAL = "CAPITAL", "CAPITAL"
    DEMO_CAPITAL = "DEMO_CAPITAL", "DEMO_CAPITAL"


PARAMETER_KEYS = tuple(ParameterKey.values)
currency_validator = RegexValidator(r"^[A-Z]{3}$", _("Use a three-letter ISO currency code, for example USD."))
vps_label_validator = RegexValidator(
    r"^[a-z0-9][a-z0-9_.-]{0,63}$",
    _("Lowercase letters, digits, dots, hyphens and underscores only (for example bot_user_12)."),
)


class ParameterDefinition(models.Model):
    """Paramètre autorisé pour un type de robot, dans une organisation.

    ``verified`` indique que l'administrateur a confirmé, sur les fichiers réels
    du VPS, que ce robot lit ce paramètre. Tant que ce n'est pas fait, le
    paramètre reste saisissable mais est signalé « à vérifier ».
    """

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="+")
    robot_type = models.CharField(_("robot"), max_length=16, choices=RobotType.choices)
    key = models.CharField(_("parameter"), max_length=32, choices=ParameterKey.choices)
    enabled = models.BooleanField(_("used by this robot"), default=True)
    verified = models.BooleanField(_("verified on the real files"), default=False)
    unit = models.CharField(_("unit"), max_length=20, blank=True)
    min_value = models.DecimalField(_("minimum"), max_digits=18, decimal_places=6, null=True, blank=True, default=Decimal("0"))
    max_value = models.DecimalField(_("maximum"), max_digits=18, decimal_places=6, null=True, blank=True)
    verification_reference = models.CharField(
        _("verification reference"), max_length=200, blank=True,
        help_text=_("File and line checked, date and author. Never a value or a secret."),
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["robot_type", "key"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "robot_type", "key"], name="bots_paramdef_unique"),
            models.CheckConstraint(condition=Q(key__in=PARAMETER_KEYS), name="bots_paramdef_whitelist"),
            models.CheckConstraint(
                condition=Q(min_value__isnull=True) | Q(max_value__isnull=True) | Q(min_value__lte=models.F("max_value")),
                name="bots_paramdef_bounds",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_robot_type_display()} · {self.key}"


class BotStatus(models.TextChoices):
    """Statuts administratifs déclarés. Ils ne décrivent jamais l'état réel du VPS."""

    TO_CONFIGURE = "to_configure", _("To configure")
    APPLIED = "applied", _("Configuration applied")
    MODIFICATION_REQUESTED = "modification_requested", _("Change requested")
    PAUSED = "paused", _("Paused")
    DISABLED = "disabled", _("Disabled")


class Override(models.TextChoices):
    NONE = "none", _("None")
    PAUSED = "paused", _("Paused")
    DISABLED = "disabled", _("Disabled")


class BotUser(models.Model):
    """Fiche administrative d'un utilisateur de robot (sans compte de connexion)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")
    # Référence vers la fiche principale de partners : aucune donnée personnelle copiée.
    affiliate = models.OneToOneField(
        "partners.Affiliate", on_delete=models.PROTECT, related_name="+", verbose_name=_("affiliate")
    )
    wants_bot = models.BooleanField(_("wants to use a robot"), default=True)
    robot_type = models.CharField(_("robot"), max_length=16, choices=RobotType.choices, blank=True)
    vps_label = models.CharField(
        _("VPS user label"), max_length=64, blank=True, validators=[vps_label_validator],
        help_text=_("Optional label of the robot user on the VPS. Never a password or token."),
    )
    admin_note = models.TextField(_("administrative note"), max_length=1000, blank=True)

    override = models.CharField(max_length=16, choices=Override.choices, default=Override.NONE)
    override_reason = models.CharField(max_length=300, blank=True)
    override_at = models.DateTimeField(null=True, blank=True)
    override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    # Valeurs calculées par services.recompute_status (jamais saisies à la main).
    status = models.CharField(_("status"), max_length=32, choices=BotStatus.choices, default=BotStatus.TO_CONFIGURE)
    current_account_type = models.CharField(max_length=8, choices=AccountType.choices, blank=True)
    pending_since = models.DateTimeField(null=True, blank=True)
    last_applied_on = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("robot user")
        verbose_name_plural = _("robot users")
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["organization", "status"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(override="none") | ~Q(override_reason=""), name="bots_botuser_override_reason"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.affiliate} · {self.get_robot_type_display() or '—'}"


class ConfigurationVersion(models.Model):
    """Version de configuration déclarée. Immuable une fois validée (renforcé en base)."""

    class State(models.TextChoices):
        DRAFT = "draft", _("Draft")
        VALIDATED = "validated", _("Validated")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")
    bot_user = models.ForeignKey(BotUser, on_delete=models.PROTECT, related_name="versions")
    number = models.PositiveIntegerField(_("version"))
    state = models.CharField(_("state"), max_length=16, choices=State.choices, default=State.DRAFT)
    robot_type = models.CharField(_("robot"), max_length=16, choices=RobotType.choices)
    account_type = models.CharField(_("account type"), max_length=8, choices=AccountType.choices, default=AccountType.DEMO)
    reference_capital = models.DecimalField(
        _("reference capital"), max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    currency = models.CharField(_("currency"), max_length=3, default="USD", validators=[currency_validator])
    admin_note = models.TextField(_("administrative note"), max_length=1000, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    # Déclaration administrative du compte réel (crm_admin uniquement).
    real_confirmed_at = models.DateTimeField(null=True, blank=True)
    real_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    real_declared_on = models.DateField(null=True, blank=True)
    real_declaration_note = models.CharField(max_length=500, blank=True)
    real_confirmation_wording = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = _("configuration version")
        verbose_name_plural = _("configuration versions")
        ordering = ["-number"]
        constraints = [
            models.UniqueConstraint(fields=["bot_user", "number"], name="bots_version_number_unique"),
            models.UniqueConstraint(fields=["bot_user"], condition=Q(state="draft"), name="bots_version_one_draft"),
            models.CheckConstraint(
                condition=Q(state="draft") | (Q(validated_at__isnull=False) & Q(reference_capital__isnull=False)),
                name="bots_version_validated_complete",
            ),
            models.CheckConstraint(
                condition=Q(state="draft")
                | Q(account_type="demo")
                | (
                    Q(real_confirmed_at__isnull=False)
                    & Q(real_confirmed_by__isnull=False)
                    & Q(real_declared_on__isnull=False)
                    & ~Q(real_declaration_note="")
                ),
                name="bots_version_real_declared",
            ),
        ]

    def __str__(self) -> str:
        return f"v{self.number} · {self.bot_user}"

    @property
    def is_draft(self) -> bool:
        return self.state == self.State.DRAFT

    @property
    def is_real(self) -> bool:
        return self.account_type == AccountType.REAL


class ParameterValue(models.Model):
    """Valeur numérique d'un paramètre autorisé. Immuable avec sa version validée."""

    version = models.ForeignKey(ConfigurationVersion, on_delete=models.CASCADE, related_name="parameters")
    key = models.CharField(max_length=32, choices=ParameterKey.choices)
    value = models.DecimalField(max_digits=18, decimal_places=6)
    unit = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(fields=["version", "key"], name="bots_paramvalue_unique"),
            models.CheckConstraint(condition=Q(key__in=PARAMETER_KEYS), name="bots_paramvalue_whitelist"),
        ]


class ApplicationDeclaration(AppendOnlyModel):
    """Déclaration administrative : « cette version a été appliquée sur le VPS ».

    La plateforme ne vérifie rien. Une erreur se corrige par une nouvelle ligne
    de type correction ; la déclaration d'origine reste dans l'historique.
    """

    class Kind(models.TextChoices):
        APPLIED = "applied", _("Declared applied")
        CORRECTION = "correction", _("Correction")

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")
    version = models.ForeignKey(ConfigurationVersion, on_delete=models.PROTECT, related_name="declarations")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    applied_on = models.DateField(_("date applied on the VPS"), null=True, blank=True)
    corrects = models.OneToOneField(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="correction"
    )
    note = models.CharField(_("note"), max_length=500, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["-recorded_at"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(kind="applied") & Q(applied_on__isnull=False) & Q(corrects__isnull=True))
                | (Q(kind="correction") & Q(corrects__isnull=False) & ~Q(note="")),
                name="bots_declaration_kind_fields",
            ),
        ]


class StatusEvent(AppendOnlyModel):
    """Historique des pauses, désactivations et réactivations."""

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")
    bot_user = models.ForeignKey(BotUser, on_delete=models.PROTECT, related_name="status_events")
    from_override = models.CharField(max_length=16, choices=Override.choices)
    to_override = models.CharField(max_length=16, choices=Override.choices)
    reason = models.CharField(max_length=300)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
