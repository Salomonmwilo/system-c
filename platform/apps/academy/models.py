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


class Enrollment(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", _("Requested")
        ACTIVE = "active", _("Active")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="enrollments")
    # Référence vers la fiche principale de partners si l'apprenant est aussi affilié.
    affiliate = models.ForeignKey("partners.Affiliate", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(affiliate__isnull=False) | models.Q(user__isnull=False),
                name="academy_enrollment_has_person",
            )
        ]
