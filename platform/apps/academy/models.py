"""Module academy : programmes éducatifs, dont SYSTEM-C Method.

Six domaines restent séparés :
1. catalogue : ``Program`` ;
2. contenu pédagogique : ``Course`` (une étape), ``Lesson``, ``Resource`` ;
3. offres commerciales : ``ProgramOffer`` (prix et devise configurables) ;
4. commandes : ``Order`` et son historique en ajout seul ``OrderAudit`` ;
5. droits d'accès : ``Enrollment`` ;
6. progression : ``LessonProgress``.

L'organisation d'une étape, d'une leçon, d'une ressource ou d'une offre est celle
de son programme. Les cohérences d'organisation, l'immuabilité des montants
commandés et l'historique en ajout seul sont aussi garantis en base de données
(migration 0005). Un affilié n'est jamais copié ici : seule une référence vers
``partners.Affiliate`` est conservée.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Deferrable, Q
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from apps.core.models import AppendOnlyModel, Language, Organization


def _localized(obj, base: str) -> str:
    english = getattr(obj, f"{base}_en", "")
    if (get_language() or "fr").startswith("en") and english:
        return english
    return getattr(obj, f"{base}_fr", "")


class PrivateStorage(FileSystemStorage):
    """Stockage sans URL publique : un fichier n'est lisible que par une vue qui vérifie les droits."""

    def url(self, name):
        raise NotImplementedError("Fichier privé : aucune URL publique.")


def private_storage():
    return PrivateStorage(location=settings.SYSTEMC_PRIVATE_MEDIA_ROOT, base_url=None)


currency_validator = RegexValidator(r"^[A-Z]{3}$", _("Use a three-letter ISO currency code, for example USD."))


class PublicationStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")
    ARCHIVED = "archived", _("Archived")


class AccessMode(models.TextChoices):
    """Durée de l'accès au contenu acheté. « Sans date d'expiration » est la règle par défaut."""

    PERMANENT = "permanent", _("No expiry date")
    LIMITED = "limited", _("Limited duration")


DEMO_PREFIX = "[Démo]"


class BilingualTitleMixin(models.Model):
    title_fr = models.CharField(_("title (French)"), max_length=200)
    title_en = models.CharField(_("title (English)"), max_length=200)

    class Meta:
        abstract = True

    @property
    def title(self) -> str:
        return _localized(self, "title")


class Program(BilingualTitleMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")
    description_fr = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    # Données de démonstration : commandables seulement quand DEBUG est actif (voir services).
    is_demo = models.BooleanField(_("demonstration data"), default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["title_fr"]
        constraints = [
            models.CheckConstraint(
                # Un programme est de démonstration si et seulement si son titre commence par « [Démo] ».
                condition=(Q(is_demo=True) & Q(title_fr__startswith=DEMO_PREFIX))
                | (Q(is_demo=False) & ~Q(title_fr__startswith=DEMO_PREFIX)),
                name="academy_program_demo_is_labelled",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class Course(BilingualTitleMixin):
    """Une étape du programme (pour SYSTEM-C Method : Comprendre, Préparer, Décider, Documenter, Évaluer)."""

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="courses")
    position = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["position"]
        constraints = [
            # Différée : permet d'échanger deux positions dans une même transaction.
            models.UniqueConstraint(
                fields=["program", "position"], name="academy_course_unique_position", deferrable=Deferrable.DEFERRED
            ),
        ]


class Lesson(BilingualTitleMixin):
    """Leçon d'une étape. Le résumé décrit l'objectif ; le contenu est le texte pédagogique rédigé."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    position = models.PositiveSmallIntegerField(default=1)
    summary_fr = models.TextField(_("summary (French)"), blank=True)
    summary_en = models.TextField(_("summary (English)"), blank=True)
    body_fr = models.TextField(_("content (French)"), blank=True)
    body_en = models.TextField(_("content (English)"), blank=True)
    is_published = models.BooleanField(_("published"), default=False)

    class Meta:
        ordering = ["position"]
        constraints = [
            # Une leçon sans contenu rédigé ne peut pas être présentée comme disponible.
            models.CheckConstraint(
                condition=Q(is_published=False) | ~Q(body_fr=""), name="academy_lesson_published_has_content"
            ),
            models.UniqueConstraint(
                fields=["course", "position"], name="academy_lesson_unique_position", deferrable=Deferrable.DEFERRED
            ),
            models.UniqueConstraint(fields=["course", "title_fr"], name="academy_lesson_unique_title"),
        ]

    @property
    def summary(self) -> str:
        return _localized(self, "summary")

    @property
    def has_english_content(self) -> bool:
        return bool(self.body_en.strip())


class ProgramOffer(models.Model):
    """Offre commerciale d'un programme. Le prix n'est jamais écrit dans le code des vues ou des gabarits."""

    Status = PublicationStatus

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="offers")
    slug = models.SlugField(max_length=100)
    name_fr = models.CharField(_("name (French)"), max_length=200)
    name_en = models.CharField(_("name (English)"), max_length=200)
    description_fr = models.TextField(_("description (French)"), blank=True)
    description_en = models.TextField(_("description (English)"), blank=True)
    price = models.DecimalField(
        _("price"), max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    currency = models.CharField(_("currency"), max_length=3, default="USD", validators=[currency_validator])
    status = models.CharField(_("status"), max_length=16, choices=Status.choices, default=Status.DRAFT)
    # Accès au contenu de l'offre : sans date d'expiration par défaut. Une durée en jours
    # est réservée aux offres dont l'accompagnement est limité dans le temps.
    access_mode = models.CharField(
        _("access duration"), max_length=10, choices=AccessMode.choices, default=AccessMode.PERMANENT
    )
    access_days = models.PositiveIntegerField(_("access length in days"), null=True, blank=True)
    position = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["program", "slug"], name="unique_program_offer_slug"),
            models.CheckConstraint(condition=Q(price__gte=0), name="academy_offer_price_not_negative"),
            models.CheckConstraint(
                condition=(Q(access_mode="permanent") & Q(access_days__isnull=True))
                # isnull explicite : en SQL, « NULL >= 1 » vaut NULL et passerait la contrainte.
                | (Q(access_mode="limited") & Q(access_days__isnull=False) & Q(access_days__gte=1)),
                name="academy_offer_access_mode_consistent",
            ),
        ]

    def access_until_from(self, start):
        """Fin d'accès pour une inscription ouverte à ``start`` ; None : sans date d'expiration."""
        if self.access_mode == AccessMode.PERMANENT:
            return None
        return start + timedelta(days=self.access_days)

    def __str__(self) -> str:
        return f"{self.program.title}, {self.name_fr}"

    @property
    def name(self) -> str:
        return _localized(self, "name")

    @property
    def description(self) -> str:
        return _localized(self, "description")


class Resource(models.Model):
    """Ressource pédagogique : document, feuille, vidéo ou exercice.

    Une ressource publiée a forcément un fichier ou une adresse. Une ressource
    « offres » n'est accessible qu'aux inscriptions actives sur l'une des offres
    qui l'incluent (voir ``apps.academy.access``).
    """

    Status = PublicationStatus

    class Category(models.TextChoices):
        GUIDE = "guide", _("Guide")
        JOURNAL = "journal", _("Tracking journal")
        RISK_SHEET = "risk_sheet", _("Capital and risk sheet")
        CHECKLIST = "checklist", _("Decision checklist")
        LEARNING_PLAN = "learning_plan", _("Learning plan")
        VIDEO = "video", _("Short video")
        EXERCISE = "exercise", _("Exercise or reflection sheet")
        DISCOVERY = "discovery", _("Free discovery resource")

    class Visibility(models.TextChoices):
        PUBLIC = "public", _("Free, no purchase needed")
        OFFERS = "offers", _("Included in selected offers")

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="resources")
    title_fr = models.CharField(_("title (French)"), max_length=200)
    title_en = models.CharField(_("title (English)"), max_length=200)
    description_fr = models.TextField(_("description (French)"), blank=True)
    description_en = models.TextField(_("description (English)"), blank=True)
    category = models.CharField(_("category"), max_length=20, choices=Category.choices, default=Category.GUIDE)
    language = models.CharField(_("language"), max_length=2, choices=Language.choices, default=Language.FR)
    version = models.PositiveSmallIntegerField(_("version"), default=1)
    file = models.FileField(_("file"), upload_to="academy/resources/%Y/%m/", storage=private_storage, blank=True)
    external_url = models.URLField(_("external address"), blank=True)
    visibility = models.CharField(
        _("visibility"), max_length=10, choices=Visibility.choices, default=Visibility.OFFERS
    )
    offers = models.ManyToManyField(
        ProgramOffer, related_name="resources", blank=True, verbose_name=_("included in offers")
    )
    status = models.CharField(_("status"), max_length=16, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(_("publication date"), null=True, blank=True)
    position = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            # Aucune ressource n'est présentée comme disponible sans fichier ni adresse.
            models.CheckConstraint(
                condition=~Q(status="published") | ~Q(file="") | ~Q(external_url=""),
                name="academy_resource_published_has_content",
            ),
            models.CheckConstraint(
                condition=~Q(status="published") | Q(published_at__isnull=False),
                name="academy_resource_published_has_date",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def title(self) -> str:
        return _localized(self, "title")

    @property
    def has_content(self) -> bool:
        return bool(self.file) or bool(self.external_url)

    def save(self, *args, **kwargs):
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class Order(models.Model):
    """Commande d'une offre.

    Le prix et la devise sont copiés de l'offre à la création, puis ne changent
    plus (garanti en base). Aucune donnée bancaire n'est enregistrée : la
    référence de transaction est celle que communique le prestataire.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        AWAITING_PAYMENT = "awaiting_payment", _("Awaiting payment")
        PAYMENT_PENDING = "payment_pending", _("Payment to verify")
        PAID = "paid", _("Paid and confirmed")
        CANCELLED = "cancelled", _("Cancelled")
        REFUNDED = "refunded", _("Refunded")

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="academy_orders")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="academy_orders")
    offer = models.ForeignKey(ProgramOffer, on_delete=models.PROTECT, related_name="orders")
    price = models.DecimalField(
        _("price at the time of the order"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    currency = models.CharField(_("currency"), max_length=3, validators=[currency_validator])
    status = models.CharField(_("status"), max_length=20, choices=Status.choices, default=Status.DRAFT)
    transaction_ref = models.CharField(
        _("transaction reference"),
        max_length=100,
        blank=True,
        help_text=_("Reference given by the payment provider. Never a card number or bank details."),
    )
    notes = models.TextField(_("administrative note"), blank=True)
    refunded_amount = models.DecimalField(_("amount refunded"), max_digits=10, decimal_places=2, default=Decimal("0"))
    # Versions des textes affichés à l'acheteur au moment de la commande (traçabilité).
    risk_notice_version = models.CharField(_("risk notice version"), max_length=20, blank=True)
    terms_version = models.CharField(_("terms of sale version"), max_length=20, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    OPEN_STATUSES = ("draft", "awaiting_payment", "payment_pending")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="academy_order_price_not_negative"),
            models.CheckConstraint(
                condition=Q(refunded_amount__gte=0) & Q(refunded_amount__lte=models.F("price")),
                name="academy_order_refund_within_price",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.pk} {self.offer.slug} {self.status}"

    @property
    def is_open(self) -> bool:
        return self.status in self.OPEN_STATUSES

    @property
    def remaining_refundable(self) -> Decimal:
        return self.price - self.refunded_amount

    @property
    def has_partial_refund(self) -> bool:
        return self.status == self.Status.PAID and self.refunded_amount > 0

    def save(self, *args, **kwargs):
        if self._state.adding:
            if self.price is None:
                self.price = self.offer.price
            if not self.currency:
                self.currency = self.offer.currency
        super().save(*args, **kwargs)


class OrderAudit(AppendOnlyModel):
    """Historique d'une commande, en ajout seul (ni modification ni suppression, renforcé en base)."""

    class Action(models.TextChoices):
        CREATED = "created", _("Created")
        STATUS_CHANGED = "status_changed", _("Status changed")
        PAYMENT_VERIFIED = "payment_verified", _("Payment verified")
        REFUNDED = "refunded", _("Full refund")
        PARTIAL_REFUND = "partial_refund", _("Partial refund")
        CANCELLED = "cancelled", _("Cancelled")
        ACCESS_REVOKED = "access_revoked", _("Access revoked")

    MONEY_ACTIONS = ("payment_verified", "refunded", "partial_refund")

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="audit_log")
    action = models.CharField(max_length=30, choices=Action.choices)
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    reference = models.CharField(_("transaction reference"), max_length=100, blank=True)
    amount = models.DecimalField(_("amount"), max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(_("currency"), max_length=3, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            # Une confirmation ou un remboursement porte toujours un auteur, une note, un montant et une devise.
            models.CheckConstraint(
                condition=~Q(action__in=("payment_verified", "refunded", "partial_refund"))
                | (Q(actor__isnull=False) & ~Q(notes="") & Q(amount__gt=0) & ~Q(currency="")),
                name="academy_orderaudit_money_action_complete",
            ),
            models.CheckConstraint(
                condition=~Q(action="cancelled") | Q(actor__isnull=False),
                name="academy_orderaudit_cancel_has_actor",
            ),
            # Une révocation d'accès est toujours attribuée et motivée.
            models.CheckConstraint(
                condition=~Q(action="access_revoked") | (Q(actor__isnull=False) & ~Q(notes="")),
                name="academy_orderaudit_revocation_complete",
            ),
        ]


class Enrollment(models.Model):
    """Droit d'accès d'une personne à un programme, selon l'offre achetée.

    Une inscription liée à une commande ne donne accès que si la commande est
    payée et confirmée : une commande en attente, annulée ou remboursée ne donne
    aucun accès, quel que soit le statut de l'inscription.
    """

    class Status(models.TextChoices):
        REQUESTED = "requested", _("Enrolment requested")
        ACTIVE = "active", _("Enrolment active")
        COMPLETED = "completed", _("Enrolment completed")
        CANCELLED = "cancelled", _("Enrolment cancelled")
        SUSPENDED = "suspended", _("Enrolment suspended")
        REVOKED = "revoked", _("Access revoked")

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="enrollments")
    # Référence vers la fiche principale de partners si l'apprenant est aussi affilié.
    affiliate = models.ForeignKey("partners.Affiliate", on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    offer = models.ForeignKey(ProgramOffer, on_delete=models.PROTECT, null=True, blank=True, related_name="enrollments")
    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=True, blank=True, related_name="enrollments")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED)
    # Représentation explicite de la durée : « sans date d'expiration » n'a pas de date de fin,
    # « durée limitée » en a toujours une.
    access_mode = models.CharField(
        _("access duration"), max_length=10, choices=AccessMode.choices, default=AccessMode.PERMANENT
    )
    access_until = models.DateTimeField(_("access expires"), null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(Q(access_mode="permanent") & Q(access_until__isnull=True))
                | (Q(access_mode="limited") & Q(access_until__isnull=False)),
                name="academy_enrollment_access_mode_consistent",
            ),
            models.CheckConstraint(
                condition=models.Q(affiliate__isnull=False) | models.Q(user__isnull=False),
                name="academy_enrollment_has_person",
            ),
            # Une commande ouvre au plus une inscription.
            models.UniqueConstraint(
                fields=["order"], condition=Q(order__isnull=False), name="academy_enrollment_one_per_order"
            ),
        ]

    def is_access_valid(self) -> bool:
        if self.status != self.Status.ACTIVE:
            return False
        if self.access_until and timezone.now() >= self.access_until:
            return False
        if self.order_id is not None and self.order.status != Order.Status.PAID:
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
