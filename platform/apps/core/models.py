"""Fondations partagées : utilisateurs, organisations, rôles, paramètres, audit."""

import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Language(models.TextChoices):
    FR = "fr", _("French")
    EN = "en", _("English")


class UserManager(BaseUserManager):
    use_in_migrations = True

    @staticmethod
    def normalize_login(email: str) -> str:
        return BaseUserManager.normalize_email(email or "").strip().lower()

    def get_by_natural_key(self, username):
        return self.get(email__iexact=self.normalize_login(username))

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Une adresse électronique est obligatoire.")
        user = self.model(email=self.normalize_login(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Un super-utilisateur doit avoir is_staff et is_superuser.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Compte de connexion. L'identifiant est l'adresse électronique."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True)
    full_name = models.CharField(_("full name"), max_length=150)
    preferred_language = models.CharField(
        _("preferred language"), max_length=5, choices=Language.choices, default=Language.FR
    )
    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(_("staff status"), default=False)
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [models.UniqueConstraint(Lower("email"), name="core_user_email_ci_unique")]

    def clean(self):
        super().clean()
        self.email = UserManager.normalize_login(self.email)

    def __str__(self) -> str:
        return self.full_name or self.email

    def get_full_name(self) -> str:
        return self.full_name

    def get_short_name(self) -> str:
        return self.full_name.split(" ")[0] if self.full_name else self.email


class Organization(models.Model):
    """Frontière d'isolation des données (tenant)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("name"), max_length=150)
    slug = models.SlugField(_("identifier"), max_length=60, unique=True)
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Role(models.TextChoices):
    ORG_ADMIN = "org_admin", _("Organization administrator")
    CRM_ADMIN = "crm_admin", _("CRM administrator")
    CRM_OPERATOR = "crm_operator", _("CRM operator")
    CRM_VIEWER = "crm_viewer", _("CRM viewer")
    PARTNER_MANAGER = "partner_manager", _("Partner manager")
    PARTNER_ADVISOR = "partner_advisor", _("Partner advisor")
    ACADEMY_INSTRUCTOR = "academy_instructor", _("Academy instructor")
    ACADEMY_STUDENT = "academy_student", _("Academy student")


class Membership(models.Model):
    """Rôle d'un utilisateur dans une organisation (une ligne par rôle)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(_("role"), max_length=32, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = _("membership")
        verbose_name_plural = _("memberships")
        constraints = [
            models.UniqueConstraint(fields=["user", "organization", "role"], name="core_membership_unique_role"),
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.organization} · {self.role}"


def threshold_field(verbose_name, default, minimum, maximum):
    return models.PositiveSmallIntegerField(
        verbose_name,
        default=default,
        validators=[MinValueValidator(minimum), MaxValueValidator(maximum)],
    )


THRESHOLD_BOUNDS = {
    "contact_stale_days": (30, 7, 180),
    "modification_pending_days": (7, 1, 60),
    "configuration_review_days": (30, 7, 365),
    "registration_stuck_days": (7, 1, 60),
    "verification_stuck_days": (14, 1, 90),
}


class OrganizationSettings(models.Model):
    """Paramètres communs d'une organisation, dont les seuils d'alerte."""

    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name="settings")
    contact_stale_days = threshold_field(_("No contact with the affiliate for"), *THRESHOLD_BOUNDS["contact_stale_days"])
    modification_pending_days = threshold_field(
        _("Change request pending for"), *THRESHOLD_BOUNDS["modification_pending_days"]
    )
    configuration_review_days = threshold_field(
        _("Last declared configuration older than"), *THRESHOLD_BOUNDS["configuration_review_days"]
    )
    registration_stuck_days = threshold_field(
        _("Registration unfinished for"), *THRESHOLD_BOUNDS["registration_stuck_days"]
    )
    verification_stuck_days = threshold_field(
        _("Verification unfinished for"), *THRESHOLD_BOUNDS["verification_stuck_days"]
    )
    default_currency = models.CharField(_("default currency"), max_length=3, default="USD")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = _("organization settings")
        verbose_name_plural = _("organization settings")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(contact_stale_days__gte=7, contact_stale_days__lte=180),
                name="core_settings_contact_bounds",
            ),
            models.CheckConstraint(
                condition=models.Q(modification_pending_days__gte=1, modification_pending_days__lte=60),
                name="core_settings_modification_bounds",
            ),
            models.CheckConstraint(
                condition=models.Q(configuration_review_days__gte=7, configuration_review_days__lte=365),
                name="core_settings_review_bounds",
            ),
            models.CheckConstraint(
                condition=models.Q(registration_stuck_days__gte=1, registration_stuck_days__lte=60),
                name="core_settings_registration_bounds",
            ),
            models.CheckConstraint(
                condition=models.Q(verification_stuck_days__gte=1, verification_stuck_days__lte=90),
                name="core_settings_verification_bounds",
            ),
        ]

    @classmethod
    def for_organization(cls, organization: Organization) -> "OrganizationSettings":
        obj, _created = cls.objects.get_or_create(
            organization=organization,
            defaults={"default_currency": getattr(settings, "SYSTEMC_DEFAULT_CURRENCY", "USD")},
        )
        return obj


class AppendOnlyModel(models.Model):
    """Modèle en ajout seul : ni modification ni suppression (renforcé en base)."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionError(f"{type(self).__name__} est en ajout seul : modification interdite.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError(f"{type(self).__name__} est en ajout seul : suppression interdite.")


class AuditLog(AppendOnlyModel):
    """Journal des actions administratives. Aucune donnée secrète, aucune note complète."""

    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, null=True, blank=True, related_name="audit_entries"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=64, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = _("audit entry")
        verbose_name_plural = _("audit entries")
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["organization", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action}"
