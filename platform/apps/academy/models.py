"""Structure initiale du module academy (fonctionnalités complètes à venir).

Les contenus sont bilingues dès la conception (champs _fr et _en). Une
inscription peut référencer la fiche affilié de partners, sans copie.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from apps.core.models import Organization


class BilingualTitleMixin(models.Model):
    title_fr = models.CharField(_("title (French)"), max_length=200)
    title_en = models.CharField(_("title (English)"), max_length=200)

    class Meta:
        abstract = True

    @property
    def title(self) -> str:
        return self.title_en if (get_language() or "fr").startswith("en") and self.title_en else self.title_fr


class Program(BilingualTitleMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")
    description_fr = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["title_fr"]

    def __str__(self) -> str:
        return self.title


class Course(BilingualTitleMixin):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="courses")
    position = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["position"]


class Lesson(BilingualTitleMixin):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    position = models.PositiveSmallIntegerField(default=1)
    body_fr = models.TextField(blank=True)
    body_en = models.TextField(blank=True)

    class Meta:
        ordering = ["position"]


class ProgramOffer(models.Model):
    """Offre commerciale d'un programme (ex: Starter, Complete, Guided pour SYSTEM-C Method)."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")
        ARCHIVED = "archived", _("Archived")

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="offers")
    slug = models.SlugField(max_length=100)  # starter, complete, guided
    name_fr = models.CharField(_("name (French)"), max_length=200)
    name_en = models.CharField(_("name (English)"), max_length=200)
    description_fr = models.TextField(_("description (French)"), blank=True)
    description_en = models.TextField(_("description (English)"), blank=True)
    price_usd = models.DecimalField(_("price (USD)"), max_digits=10, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    position = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["program", "slug"], name="unique_program_offer_slug")
        ]

    def __str__(self) -> str:
        return f"{self.program.title} — {self.name_fr}"

    @property
    def name(self) -> str:
        return self.name_en if (get_language() or "fr").startswith("en") and self.name_en else self.name_fr


class Resource(models.Model):
    """Ressource pédagogique : guide, vidéo, feuille de calcul, etc."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")
        ARCHIVED = "archived", _("Archived")

    class ResourceType(models.TextChoices):
        GUIDE = "guide", _("Guide")
        VIDEO = "video", _("Video")
        WORKSHEET = "worksheet", _("Worksheet")
        CHECKLIST = "checklist", _("Checklist")
        EXERCISE = "exercise", _("Exercise")
        OTHER = "other", _("Other")

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="resources")
    title_fr = models.CharField(_("title (French)"), max_length=200)
    title_en = models.CharField(_("title (English)"), max_length=200)
    description_fr = models.TextField(_("description (French)"), blank=True)
    description_en = models.TextField(_("description (English)"), blank=True)
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices, default=ResourceType.GUIDE)
    file_path = models.FileField(_("file"), upload_to="academy/resources/%Y/%m/", blank=True)
    external_url = models.URLField(_("external URL"), blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    position = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]

    def __str__(self) -> str:
        return self.title

    @property
    def title(self) -> str:
        return self.title_en if (get_language() or "fr").startswith("en") and self.title_en else self.title_fr


class Order(models.Model):
    """Commande d'une offre (achat du programme)."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        AWAITING_PAYMENT = "awaiting_payment", _("Awaiting payment")
        PAYMENT_PENDING = "payment_pending", _("Payment pending verification")
        PAID = "paid", _("Paid and confirmed")
        CANCELLED = "cancelled", _("Cancelled")
        REFUNDED = "refunded", _("Refunded")

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="academy_orders")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="academy_orders")
    offer = models.ForeignKey(ProgramOffer, on_delete=models.PROTECT, related_name="orders")
    price_usd = models.DecimalField(_("price at purchase (USD)"), max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    transaction_ref = models.CharField(_("transaction reference"), max_length=100, blank=True)
    notes = models.TextField(_("admin notes"), blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order {self.id} — {self.user.email} — {self.offer.name_fr}"


class OrderAudit(models.Model):
    """Trace des modifications de commande pour la conformité et l'audit."""

    class Action(models.TextChoices):
        CREATED = "created", _("Created")
        STATUS_CHANGED = "status_changed", _("Status changed")
        PAYMENT_VERIFIED = "payment_verified", _("Payment verified")
        REFUNDED = "refunded", _("Refunded")
        CANCELLED = "cancelled", _("Cancelled")

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="audit_log")
    action = models.CharField(max_length=30, choices=Action.choices)
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]


class Enrollment(models.Model):
    """Inscription à un programme avec accès basé sur l'offre achetée."""

    class Status(models.TextChoices):
        REQUESTED = "requested", _("Requested")
        ACTIVE = "active", _("Active")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")
        SUSPENDED = "suspended", _("Suspended")

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="enrollments")
    affiliate = models.ForeignKey("partners.Affiliate", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    offer = models.ForeignKey(ProgramOffer, on_delete=models.PROTECT, null=True, blank=True, related_name="enrollments")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="enrollments")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED)
    access_until = models.DateTimeField(_("access expires"), null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(affiliate__isnull=False) | models.Q(user__isnull=False),
                name="academy_enrollment_has_person",
            )
        ]

    def is_access_valid(self) -> bool:
        """Vérifier si l'accès est toujours valide."""
        if self.status != self.Status.ACTIVE:
            return False
        if self.access_until and timezone.now() > self.access_until:
            return False
        return True


class LessonProgress(models.Model):
    """Suivi de progression de l'apprenant dans les leçons."""

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress_records")
    completed_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("enrollment", "lesson")

    def is_completed(self) -> bool:
        return self.completed_at is not None
