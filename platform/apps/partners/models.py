"""Module partners : propriétaire de la fiche principale de chaque affilié.

Les autres modules (bots, academy) référencent ``Affiliate`` par identifiant et
ne copient jamais ses données personnelles.
"""

import uuid

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import AppendOnlyModel, Language, Organization

country_validator = RegexValidator(r"^[A-Z]{2}$", _("Use a two-letter ISO country code, for example CD."))


class ReferralLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="referral_links")
    label = models.CharField(_("label"), max_length=120)
    url = models.URLField(_("referral link"), max_length=500)
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        verbose_name = _("referral link")
        verbose_name_plural = _("referral links")
        ordering = ["label"]

    def __str__(self) -> str:
        return self.label


class Affiliate(models.Model):
    class Status(models.TextChoices):
        PROSPECT = "prospect", _("Prospect")
        ACTIVE = "active", _("Active")
        INACTIVE = "inactive", _("Inactive")

    class Registration(models.TextChoices):
        NOT_STARTED = "not_started", _("Not started")
        DECLARED = "declared_by_affiliate", _("Declared by the affiliate")
        ACCOUNT_CREATED = "account_created", _("Deriv account created (declared)")

    class Verification(models.TextChoices):
        NOT_REQUESTED = "not_requested", _("Not requested")
        REQUESTED = "requested", _("Requested")
        IN_PROGRESS = "in_progress", _("In progress")
        TO_REVIEW = "to_review", _("To review")
        VALIDATED = "validated", _("Validated")
        REJECTED = "rejected", _("Rejected")

    class Demo(models.TextChoices):
        NOT_OPENED = "not_opened", _("Not opened")
        OPENED = "opened", _("Demo account opened (declared)")

    VERIFICATION_FINAL = (Verification.VALIDATED, Verification.REJECTED)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="affiliates")
    display_name = models.CharField(_("name"), max_length=120)
    email = models.EmailField(_("email address"), blank=True)
    phone = models.CharField(_("phone"), max_length=40, blank=True)
    country = models.CharField(_("country"), max_length=2, blank=True, validators=[country_validator])
    preferred_language = models.CharField(
        _("preferred language"), max_length=5, choices=Language.choices, default=Language.FR
    )
    status = models.CharField(_("status"), max_length=16, choices=Status.choices, default=Status.ACTIVE)
    referral_link = models.ForeignKey(
        ReferralLink, on_delete=models.SET_NULL, null=True, blank=True, related_name="affiliates",
        verbose_name=_("referral link"),
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        verbose_name=_("assigned to"),
    )

    registration_status = models.CharField(
        _("Deriv registration"), max_length=32, choices=Registration.choices, default=Registration.NOT_STARTED
    )
    registration_updated_on = models.DateField(null=True, blank=True)
    verification_status = models.CharField(
        _("verification"), max_length=32, choices=Verification.choices, default=Verification.NOT_REQUESTED
    )
    verification_updated_on = models.DateField(null=True, blank=True)
    demo_status = models.CharField(_("demo account"), max_length=32, choices=Demo.choices, default=Demo.NOT_OPENED)
    demo_updated_on = models.DateField(null=True, blank=True)

    last_contact_at = models.DateTimeField(_("last contact"), null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = _("affiliate")
        verbose_name_plural = _("affiliates")
        ordering = ["display_name"]
        constraints = [
            models.UniqueConstraint(
                "organization",
                Lower("email"),
                condition=~models.Q(email=""),
                name="partners_affiliate_email_unique_per_org",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "registration_status"]),
            models.Index(fields=["organization", "verification_status"]),
        ]

    def __str__(self) -> str:
        return self.display_name

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    @property
    def registration_pending(self) -> bool:
        return self.registration_status != self.Registration.ACCOUNT_CREATED

    @property
    def verification_pending(self) -> bool:
        return (
            self.registration_status == self.Registration.ACCOUNT_CREATED
            and self.verification_status not in self.VERIFICATION_FINAL
        )


class Track(models.TextChoices):
    REGISTRATION = "registration", _("Deriv registration")
    VERIFICATION = "verification", _("Verification")
    DEMO = "demo", _("Demo account")


TRACK_FIELDS = {
    Track.REGISTRATION: ("registration_status", "registration_updated_on", Affiliate.Registration),
    Track.VERIFICATION: ("verification_status", "verification_updated_on", Affiliate.Verification),
    Track.DEMO: ("demo_status", "demo_updated_on", Affiliate.Demo),
}


class TrackEvent(AppendOnlyModel):
    """Historique daté du parcours d'inscription, de vérification et de démo."""

    class Source(models.TextChoices):
        AFFILIATE = "affiliate", _("The affiliate")
        ADMINISTRATOR = "administrator", _("An administrator")
        DERIV_SUPPORT = "deriv_support", _("Deriv support")

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")
    affiliate = models.ForeignKey(Affiliate, on_delete=models.PROTECT, related_name="track_events")
    track = models.CharField(_("step"), max_length=16, choices=Track.choices)
    value = models.CharField(_("status"), max_length=32)
    previous_value = models.CharField(max_length=32, blank=True)
    declared_on = models.DateField(_("date"))
    source = models.CharField(_("source"), max_length=16, choices=Source.choices, default=Source.ADMINISTRATOR)
    note = models.CharField(_("note"), max_length=500, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["-declared_on", "-recorded_at"]

    def value_label(self) -> str:
        choices = TRACK_FIELDS[self.track][2]
        return dict(choices.choices).get(self.value, self.value)

    def previous_label(self) -> str:
        choices = TRACK_FIELDS[self.track][2]
        return dict(choices.choices).get(self.previous_value, self.previous_value)


class Interaction(AppendOnlyModel):
    """Contact ou note de suivi. Les notes internes ne comptent pas comme contact."""

    class Kind(models.TextChoices):
        CALL = "call", _("Call")
        MESSAGE = "message", _("Message")
        EMAIL = "email", _("Email")
        MEETING = "meeting", _("Meeting")
        NOTE = "note", _("Internal note")
        OTHER = "other", _("Other contact")

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")
    affiliate = models.ForeignKey(Affiliate, on_delete=models.PROTECT, related_name="interactions")
    kind = models.CharField(_("type"), max_length=16, choices=Kind.choices)
    occurred_at = models.DateTimeField(_("date"))
    summary = models.TextField(_("summary"), max_length=2000)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]

    @property
    def counts_as_contact(self) -> bool:
        return self.kind != self.Kind.NOTE


class FollowUp(models.Model):
    """Relance ou action planifiée pour un affilié."""

    class Status(models.TextChoices):
        OPEN = "open", _("To do")
        DONE = "done", _("Done")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")
    affiliate = models.ForeignKey(Affiliate, on_delete=models.PROTECT, related_name="followups")
    title = models.CharField(_("action"), max_length=160)
    due_on = models.DateField(_("due date"))
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        verbose_name=_("assigned to"),
    )
    status = models.CharField(_("status"), max_length=16, choices=Status.choices, default=Status.OPEN)
    note = models.CharField(_("details"), max_length=500, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["due_on", "created_at"]
        indexes = [models.Index(fields=["organization", "status", "due_on"])]

    @property
    def is_overdue(self) -> bool:
        return self.status == self.Status.OPEN and self.due_on < timezone.localdate()
