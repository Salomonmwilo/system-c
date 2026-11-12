"""Tests du module academy (SYSTEM-C Method) : droits d'accès, intégrité, fichiers privés, isolation."""

import tempfile
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import CommandError, call_command
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.academy import services
from apps.academy.access import active_enrollments, can_access_resource
from apps.academy.forms import RefundForm
from apps.academy.models import (
    AccessMode,
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Order,
    OrderAudit,
    PrivateStorage,
    Program,
    ProgramOffer,
    Resource,
    private_storage,
)
from apps.bots.models import BotUser
from apps.core.models import Role
from apps.core.models import AuditLog, Membership, User
from apps.core.testing import fake_request, login, make_org, make_user
from apps.partners.models import Affiliate
from apps.partners.tests import make_affiliate

R = Role


class AcademyTestCase(TestCase):
    """Un programme avec les trois offres et une ressource par niveau d'accès."""

    def setUp(self):
        self.org = make_org()
        self.admin = make_user(self.org, R.ORG_ADMIN, R.CRM_ADMIN)
        self.buyer = make_user(self.org, R.ACADEMY_STUDENT)
        self.program = Program.objects.create(organization=self.org, title_fr="SYSTEM-C Method", title_en="SYSTEM-C Method")
        self.starter = self.offer("starter", "9.00")
        self.complete = self.offer("complete", "29.00")
        self.guided = self.offer("guided", "79.00")
        self.free = self.resource("Gratuite", Resource.Visibility.PUBLIC)
        self.complete_res = self.resource("Guide principal", offers=[self.complete, self.guided])
        self.guided_res = self.resource("Support d'atelier", offers=[self.guided])

    def offer(self, slug, price, program=None):
        return ProgramOffer.objects.create(
            program=program or self.program, slug=slug, name_fr=slug, name_en=slug, price=Decimal(price)
        )

    def resource(self, title, visibility=Resource.Visibility.OFFERS, offers=(), status=Resource.Status.PUBLISHED, program=None):
        res = Resource.objects.create(
            program=program or self.program,
            title_fr=title,
            title_en=title,
            visibility=visibility,
            status=status,
            external_url="https://example.org/ressource" if status == Resource.Status.PUBLISHED else "",
        )
        res.offers.set(offers)
        return res

    def buy(self, offer, status=Order.Status.PAID, user=None):
        """Commande payée : confirmée par le service, comme dans l'application.

        Commande non payée : créée telle quelle avec une inscription active, pour
        vérifier que l'inscription seule ne donne aucun accès.
        """
        user = user or self.buyer
        org = offer.program.organization
        if status == Order.Status.PAID:
            order = Order.objects.create(organization=org, user=user, offer=offer, status=Order.Status.AWAITING_PAYMENT)
            admin = self.admin if org == self.org else make_user(org, R.ORG_ADMIN)
            order, _ = services.confirm_payment(
                request=fake_request(admin, org), order=order, note="Test : réception vérifiée.", reference="TEST-1"
            )
            return order, order.enrollments.get()
        order = Order.objects.create(organization=org, user=user, offer=offer, status=status)
        enrollment = Enrollment.objects.create(
            organization=org, program=offer.program, user=user, offer=offer, order=order, status=Enrollment.Status.ACTIVE
        )
        return order, enrollment


class AccessScenarioTests(AcademyTestCase):
    def test_free_resource_is_open_without_account(self):
        self.assertTrue(can_access_resource(AnonymousUser(), self.free))
        self.assertFalse(can_access_resource(AnonymousUser(), self.complete_res))

    def test_buyer_needs_neither_affiliate_record_nor_robot(self):
        self.buy(self.complete)
        self.assertTrue(can_access_resource(self.buyer, self.complete_res))
        self.assertFalse(Affiliate.objects.filter(organization=self.org).exists())
        self.assertFalse(BotUser.objects.filter(organization=self.org).exists())

    def test_unpaid_order_gives_no_paid_access(self):
        for status in (Order.Status.DRAFT, Order.Status.AWAITING_PAYMENT, Order.Status.PAYMENT_PENDING):
            with self.subTest(status=status):
                user = make_user(self.org, R.ACADEMY_STUDENT)
                _, enrollment = self.buy(self.complete, status=status, user=user)
                self.assertEqual(enrollment.status, Enrollment.Status.ACTIVE)
                self.assertFalse(enrollment.is_access_valid())
                self.assertFalse(can_access_resource(user, self.complete_res))
                self.assertTrue(can_access_resource(user, self.free))

    def test_paid_offer_opens_only_its_own_resources(self):
        self.buy(self.complete)
        self.assertTrue(can_access_resource(self.buyer, self.complete_res))
        self.assertFalse(can_access_resource(self.buyer, self.guided_res), "Complete ne doit pas ouvrir Guided")
        starter_user = make_user(self.org, R.ACADEMY_STUDENT)
        self.buy(self.starter, user=starter_user)
        self.assertFalse(can_access_resource(starter_user, self.complete_res))

    def test_cancelled_or_refunded_order_removes_access(self):
        request = fake_request(self.admin, self.org)
        user = make_user(self.org, R.ACADEMY_STUDENT)
        order, enrollment = self.buy(self.complete, user=user, status=Order.Status.AWAITING_PAYMENT)
        services.cancel_order(request=request, order=order, reason="Test")
        self.assertFalse(can_access_resource(user, self.complete_res))
        user = make_user(self.org, R.ACADEMY_STUDENT)
        order, enrollment = self.buy(self.complete, user=user)
        self.assertTrue(can_access_resource(user, self.complete_res))
        services.refund(request=request, order=order, amount=order.price, reason="Test")
        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_access_valid())
        self.assertFalse(can_access_resource(user, self.complete_res))
        # L'historique d'inscription reste en place.
        self.assertTrue(Enrollment.objects.filter(pk=enrollment.pk, order=order).exists())

    def test_expired_or_suspended_enrollment_gives_no_access(self):
        _, enrollment = self.buy(self.complete)
        enrollment.access_mode = AccessMode.LIMITED
        enrollment.access_until = timezone.now() - timedelta(minutes=1)
        enrollment.save()
        self.assertFalse(can_access_resource(self.buyer, self.complete_res))
        enrollment.access_mode = AccessMode.PERMANENT
        enrollment.access_until = None
        enrollment.status = Enrollment.Status.SUSPENDED
        enrollment.save()
        self.assertFalse(can_access_resource(self.buyer, self.complete_res))

    def test_unpublished_or_empty_resource_is_never_accessible(self):
        self.buy(self.guided)
        draft = self.resource("Brouillon", offers=[self.guided], status=Resource.Status.DRAFT)
        self.assertFalse(can_access_resource(self.buyer, draft))

    def test_enrollment_in_another_organization_gives_nothing_here(self):
        other = make_org()
        program_b = Program.objects.create(organization=other, title_fr="B", title_en="B")
        offer_b = self.offer("complete", "29.00", program=program_b)
        user = make_user(other, R.ACADEMY_STUDENT)
        self.buy(offer_b, user=user)
        self.assertFalse(can_access_resource(user, self.complete_res))
        self.assertEqual(active_enrollments(user, self.program).count(), 0)


class OrderIntegrityTests(AcademyTestCase):
    def test_price_and_currency_are_frozen_at_order_time(self):
        order, _ = self.buy(self.complete, status=Order.Status.AWAITING_PAYMENT)
        self.assertEqual((order.price, order.currency), (Decimal("29.00"), "USD"))
        self.complete.price = Decimal("39.00")
        self.complete.save()
        order.refresh_from_db()
        self.assertEqual(order.price, Decimal("29.00"))
        for change in ({"price": Decimal("1")}, {"currency": "EUR"}, {"offer": self.guided}, {"user": self.admin}):
            with self.subTest(change=change), self.assertRaises(DatabaseError), transaction.atomic():
                Order.objects.filter(pk=order.pk).update(**change)

    def test_order_must_belong_to_the_offer_organization(self):
        other = make_org()
        with self.assertRaises(DatabaseError), transaction.atomic():
            Order.objects.create(organization=other, user=self.buyer, offer=self.complete)

    def test_only_draft_orders_can_be_deleted(self):
        draft = Order.objects.create(organization=self.org, user=self.buyer, offer=self.complete)
        draft.delete()
        paid, _ = self.buy(self.complete)
        with self.assertRaises(DatabaseError), transaction.atomic():
            Order.objects.filter(pk=paid.pk).delete()

    def test_order_history_is_append_only(self):
        order, _ = self.buy(self.complete)
        entry = order.audit_log.get(action=OrderAudit.Action.PAYMENT_VERIFIED)
        self.assertEqual((entry.actor, entry.reference), (self.admin, "TEST-1"))
        with self.assertRaises(PermissionError):
            entry.save()
        with self.assertRaises(PermissionError):
            entry.delete()
        with self.assertRaises(DatabaseError), transaction.atomic():
            OrderAudit.objects.filter(pk=entry.pk).update(notes="réécrit")
        with self.assertRaises(DatabaseError), transaction.atomic():
            OrderAudit.objects.filter(pk=entry.pk).delete()

    def test_enrollment_must_match_its_order(self):
        order = Order.objects.create(organization=self.org, user=self.buyer, offer=self.complete)
        intruder = make_user(self.org, R.ACADEMY_STUDENT)
        cases = {
            "autre acheteur": {"user": intruder, "offer": self.complete},
            "offre plus élevée": {"user": self.buyer, "offer": self.guided},
        }
        for label, fields in cases.items():
            with self.subTest(label), self.assertRaises(DatabaseError), transaction.atomic():
                Enrollment.objects.create(
                    organization=self.org, program=self.program, order=order, status=Enrollment.Status.ACTIVE, **fields
                )

    def test_one_enrollment_per_order(self):
        order, _ = self.buy(self.complete)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Enrollment.objects.create(
                organization=self.org, program=self.program, user=self.buyer, offer=self.complete, order=order
            )

    def test_enrollment_stays_inside_its_organization_and_program(self):
        other = make_org()
        program_b = Program.objects.create(organization=other, title_fr="B", title_en="B")
        offer_b = self.offer("complete", "29.00", program=program_b)
        with self.assertRaises(DatabaseError), transaction.atomic():
            Enrollment.objects.create(organization=other, program=self.program, user=self.buyer)
        with self.assertRaises(DatabaseError), transaction.atomic():
            Enrollment.objects.create(organization=self.org, program=self.program, user=self.buyer, offer=offer_b)
        foreign_affiliate = make_affiliate(other, make_user(other, R.CRM_ADMIN))
        with self.assertRaises(DatabaseError), transaction.atomic():
            Enrollment.objects.create(organization=self.org, program=self.program, affiliate=foreign_affiliate)

    def test_learner_can_be_an_existing_affiliate_without_copying_it(self):
        affiliate = make_affiliate(self.org, self.admin, display_name="Affilié existant")
        enrollment = Enrollment.objects.create(organization=self.org, program=self.program, affiliate=affiliate)
        self.assertEqual(enrollment.affiliate_id, affiliate.pk)
        names = {f.name for f in Enrollment._meta.get_fields()}
        self.assertFalse(names & {"display_name", "email", "phone", "first_name", "last_name"})


class ContentIntegrityTests(AcademyTestCase):
    def test_resource_cannot_be_published_without_file_or_address(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Resource.objects.create(program=self.program, title_fr="Vide", title_en="Empty", status=Resource.Status.PUBLISHED)

    def test_publication_date_is_set_on_publication(self):
        self.assertIsNotNone(self.complete_res.published_at)
        draft = self.resource("Brouillon", status=Resource.Status.DRAFT)
        self.assertIsNone(draft.published_at)

    def test_lesson_cannot_be_published_without_content(self):
        course = Course.objects.create(program=self.program, title_fr="Comprendre", title_en="Understand")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Lesson.objects.create(course=course, title_fr="L", title_en="L", summary_fr="Résumé", is_published=True)
        lesson = Lesson.objects.create(course=course, title_fr="L", title_en="L", body_fr="Texte rédigé.", is_published=True)
        self.assertFalse(lesson.has_english_content)

    def test_resource_only_joins_offers_of_its_program(self):
        other_program = Program.objects.create(organization=self.org, title_fr="Autre", title_en="Other")
        other_offer = self.offer("complete", "29.00", program=other_program)
        with self.assertRaises(DatabaseError), transaction.atomic():
            self.complete_res.offers.add(other_offer)

    def test_parents_do_not_move(self):
        other = make_org()
        with self.assertRaises(DatabaseError), transaction.atomic():
            Program.objects.filter(pk=self.program.pk).update(organization=other)
        other_program = Program.objects.create(organization=self.org, title_fr="Autre", title_en="Other")
        with self.assertRaises(DatabaseError), transaction.atomic():
            Resource.objects.filter(pk=self.complete_res.pk).update(program=other_program)
        with self.assertRaises(DatabaseError), transaction.atomic():
            ProgramOffer.objects.filter(pk=self.complete.pk).update(program=other_program)

    def test_progress_only_on_lessons_of_the_enrolled_program(self):
        _, enrollment = self.buy(self.complete)
        other_program = Program.objects.create(organization=self.org, title_fr="Autre", title_en="Other")
        foreign = Lesson.objects.create(
            course=Course.objects.create(program=other_program, title_fr="X", title_en="X"), title_fr="X", title_en="X"
        )
        with self.assertRaises(DatabaseError), transaction.atomic():
            LessonProgress.objects.create(enrollment=enrollment, lesson=foreign)
        own = Lesson.objects.create(
            course=Course.objects.create(program=self.program, title_fr="Y", title_en="Y"), title_fr="Y", title_en="Y"
        )
        progress = LessonProgress.objects.create(enrollment=enrollment, lesson=own)
        self.assertFalse(progress.is_completed())


class PrivateFileTests(TestCase):
    def test_resource_files_use_the_private_storage(self):
        self.assertIsInstance(Resource._meta.get_field("file").storage, PrivateStorage)

    def test_private_storage_writes_to_its_root_and_has_no_public_address(self):
        with tempfile.TemporaryDirectory() as root, override_settings(SYSTEMC_PRIVATE_MEDIA_ROOT=root):
            storage = private_storage()
            name = storage.save("academy/resources/2026/11/guide.pdf", ContentFile(b"%PDF-1.4 test"))
            stored = Path(storage.path(name))
            self.assertTrue(stored.is_file())
            self.assertTrue(str(stored).startswith(root))
            with self.assertRaises(NotImplementedError):
                storage.url(name)
            for url in ("/" + name, "/media/" + name, "/static/" + name, "/academy/" + name):
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 404)

    def test_default_private_root_is_neither_static_nor_inside_an_app(self):
        root = Path(settings.SYSTEMC_PRIVATE_MEDIA_ROOT).resolve()
        for public in [*settings.STATICFILES_DIRS, settings.STATIC_ROOT]:
            self.assertNotEqual(root, Path(public).resolve())
            self.assertFalse(str(root).startswith(str(Path(public).resolve()) + "/"))
        self.assertFalse(str(root).startswith(str((Path(settings.BASE_DIR) / "apps").resolve())))
        ignored = (Path(settings.BASE_DIR).parent / ".gitignore").read_text()
        self.assertIn("private_media/", ignored)


class NoSecretFieldTests(TestCase):
    def test_no_field_collects_credentials_or_bank_data(self):
        from django.apps import apps as django_apps

        forbidden = ("token", "password", "secret", "api_key", "apikey", "card", "iban", "cvv", "pin", "login", "account_id")
        for model in django_apps.get_app_config("academy").get_models():
            for field in model._meta.get_fields():
                with self.subTest(model=model.__name__, field=field.name):
                    self.assertFalse(any(part in field.name.lower() for part in forbidden))


class AdminSiteTests(TestCase):
    def test_django_admin_is_not_installed(self):
        """L'administration Django contournerait l'isolation par organisation (voir MVP_REPORT.md)."""
        self.assertNotIn("django.contrib.admin", settings.INSTALLED_APPS)
        self.assertEqual(self.client.get("/admin/").status_code, 404)


class AcademyIsolationTests(AcademyTestCase):
    def test_home_lists_only_programs_of_the_current_organization(self):
        other = make_org()
        Program.objects.create(organization=other, title_fr="Programme étranger", title_en="Foreign programme")
        login(self.client, self.buyer, self.org)
        response = self.client.get(reverse("academy:home"))
        self.assertContains(response, "SYSTEM-C Method")
        self.assertNotContains(response, "Programme étranger")

    def test_roles_without_academy_permission_are_refused(self):
        operator = make_user(self.org, R.CRM_OPERATOR)
        login(self.client, operator, self.org)
        self.assertEqual(self.client.get(reverse("academy:home")).status_code, 403)


class SeedCommandTests(TestCase):
    def run_seed(self, org):
        out = StringIO()
        call_command("seed_system_c_method", organization=org.slug, yes=True, stdout=out)
        return out.getvalue()

    def test_seed_creates_structure_without_inventing_content(self):
        org = make_org()
        self.run_seed(org)
        program = Program.objects.get(organization=org)
        self.assertFalse(program.is_published)
        self.assertEqual(list(program.courses.values_list("title_fr", flat=True)),
                         ["Comprendre", "Préparer", "Décider", "Documenter", "Évaluer"])
        lessons = Lesson.objects.filter(course__program=program)
        self.assertEqual(lessons.count(), 25)
        self.assertFalse(lessons.filter(is_published=True).exists())
        self.assertFalse(lessons.exclude(body_fr="").exists(), "aucun contenu pédagogique ne doit être inventé")
        self.assertFalse(lessons.filter(summary_fr="").exists())
        resources = program.resources.all()
        self.assertEqual(resources.count(), 10)
        self.assertFalse(resources.exclude(status=Resource.Status.DRAFT).exists())
        self.assertFalse(any(r.has_content for r in resources))
        free = resources.get(category=Resource.Category.DISCOVERY)
        self.assertEqual(free.visibility, Resource.Visibility.PUBLIC)
        offers = {o.slug: o for o in program.offers.all()}
        self.assertEqual({s: (o.price, o.currency, o.status) for s, o in offers.items()}, {
            "starter": (Decimal("9.00"), "USD", "draft"),
            "complete": (Decimal("29.00"), "USD", "draft"),
            "guided": (Decimal("79.00"), "USD", "draft"),
        })
        guided_only = set(offers["guided"].resources.values_list("pk", flat=True)) - set(
            offers["complete"].resources.values_list("pk", flat=True)
        )
        self.assertEqual(guided_only, set(), "le contenu numérique de Guided est celui de Complete")

    def test_seed_is_repeatable_and_keeps_manual_edits(self):
        org = make_org()
        self.run_seed(org)
        offer = ProgramOffer.objects.get(program__organization=org, slug="complete")
        offer.price = Decimal("25.00")
        offer.save()
        self.run_seed(org)
        offer.refresh_from_db()
        self.assertEqual(offer.price, Decimal("25.00"))
        self.assertEqual(Lesson.objects.filter(course__program__organization=org).count(), 25)
        self.assertEqual(Resource.objects.filter(program__organization=org).count(), 10)

    def test_seeded_texts_have_no_em_dash(self):
        org = make_org()
        self.run_seed(org)
        texts = []
        for model, fields in (
            (Course, ("title_fr", "title_en")),
            (Lesson, ("title_fr", "title_en", "summary_fr", "summary_en")),
            (Resource, ("title_fr", "title_en", "description_fr", "description_en")),
            (ProgramOffer, ("name_fr", "name_en", "description_fr", "description_en")),
        ):
            texts += [v for row in model.objects.values_list(*fields) for v in row]
        self.assertFalse([t for t in texts if "—" in t])


class MigrationTests(TransactionTestCase):
    """Rejoue 0002 → 0006 sur des données créées par la première version du module."""

    before = [("academy", "0002_extend_academy_for_commerce")]
    after = [("academy", "0006_integrity_triggers")]

    def test_existing_data_survives_the_migrations(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        old = executor.loader.project_state(self.before).apps
        org = old.get_model("core", "Organization").objects.create(name="Org", slug="org-migration")
        user = old.get_model("core", "User").objects.create(email="m@example.org", full_name="M")
        program = old.get_model("academy", "Program").objects.create(organization_id=org.pk, title_fr="SYSTEM-C Method", title_en="SYSTEM-C Method")
        course = old.get_model("academy", "Course").objects.create(program=program, title_fr="Étape 3 — DÉCIDER", title_en="Step 3 — DECIDE", position=3)
        old.get_model("academy", "Lesson").objects.create(
            course=course, position=3, title_fr="Identifier les décisions impulsives", title_en="Identify Impulse Decisions",
            body_fr="Reconnaître la peur, la cupidité et les biais.", body_en="Recognize fear, greed and biases.",
        )
        old.get_model("academy", "Resource").objects.create(
            program=program, title_fr="7 questions avant une décision (gratuit)", title_en="7 Questions Before a Decision (free)",
            resource_type="guide", description_fr="Ressource gratuite de découverte",
        )
        offer = old.get_model("academy", "ProgramOffer").objects.create(program=program, slug="complete", name_fr="Complete", name_en="Complete", price_usd=Decimal("29.00"))
        order = old.get_model("academy", "Order").objects.create(organization_id=org.pk, user_id=user.pk, offer=offer, price_usd=Decimal("29.00"), status="paid")
        old.get_model("academy", "OrderAudit").objects.create(order=order, action="payment_verified", user_id=user.pk)

        executor = MigrationExecutor(connection)
        executor.migrate(self.after)
        new = executor.loader.project_state(self.after).apps
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes()))
        course = new.get_model("academy", "Course").objects.get()
        self.assertEqual((course.title_fr, course.title_en), ("Décider", "Decide"))
        lesson = new.get_model("academy", "Lesson").objects.get()
        self.assertEqual((lesson.position, lesson.body_fr, lesson.summary_fr), (4, "", "Reconnaître la peur, la cupidité et les biais."))
        resource = new.get_model("academy", "Resource").objects.get()
        self.assertEqual((resource.category, resource.visibility), ("discovery", "public"))
        self.assertEqual(resource.title_fr, "7 questions à se poser avant une décision de trading")
        order = new.get_model("academy", "Order").objects.get()
        self.assertEqual((order.price, order.currency), (Decimal("29.00"), "USD"))
        self.assertEqual(new.get_model("academy", "OrderAudit").objects.get().actor_id, user.pk)


class PublishedOfferMixin:
    """Programme et offres publiés : seuls ceux-là peuvent être commandés."""

    def publish(self):
        Program.objects.filter(pk=self.program.pk).update(is_published=True)
        ProgramOffer.objects.filter(pk__in=[self.complete.pk, self.guided.pk]).update(status=ProgramOffer.Status.PUBLISHED)
        self.program.refresh_from_db()
        self.complete.refresh_from_db()


class PaymentConfirmationTests(PublishedOfferMixin, AcademyTestCase):
    """D1 et D6 : confirmation manuelle, réservée à payments.confirm_order."""

    def setUp(self):
        super().setUp()
        self.publish()
        self.order = Order.objects.create(organization=self.org, user=self.buyer, offer=self.complete, status=Order.Status.AWAITING_PAYMENT)
        self.url = reverse("academy:order_confirm", args=[self.order.pk])
        self.data = {"confirm-received": "on", "confirm-reference": "VIR-2026-11-0042", "confirm-note": "Virement lu sur le relevé du 11/11."}

    def test_only_org_admin_holds_the_permission(self):
        from apps.core.permissions import PERMISSIONS

        self.assertEqual(PERMISSIONS["payments.confirm_order"], frozenset({R.ORG_ADMIN}))

    def test_unauthorised_roles_cannot_confirm(self):
        for role in (R.CRM_ADMIN, R.CRM_OPERATOR, R.ACADEMY_INSTRUCTOR, R.ACADEMY_STUDENT):
            with self.subTest(role=role):
                user = make_user(self.org, role)
                login(self.client, user, self.org)
                self.assertEqual(self.client.post(self.url, self.data).status_code, 403)
                with self.assertRaises(PermissionDenied):
                    services.confirm_payment(request=fake_request(user, self.org), order=self.order, note="x")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.AWAITING_PAYMENT)

    def test_superuser_gets_no_payment_permission(self):
        root = User.objects.create_superuser(email="root@example.org", password="Root-Password-2026!", full_name="Root")
        Membership.objects.create(user=root, organization=self.org, role=R.ACADEMY_STUDENT)
        login(self.client, root, self.org)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)
        self.assertEqual(self.client.get(reverse("academy:order_list")).status_code, 403)

    def test_admin_of_another_organization_cannot_confirm(self):
        other = make_org()
        foreign_admin = make_user(other, R.ORG_ADMIN)
        login(self.client, foreign_admin, other)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 404)
        self.assertEqual(self.client.get(reverse("academy:order_detail", args=[self.order.pk])).status_code, 404)
        with self.assertRaises(PermissionDenied):
            services.confirm_payment(request=fake_request(foreign_admin, other), order=self.order, note="x")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.AWAITING_PAYMENT)

    def test_confirmation_is_audited_and_opens_only_the_offer(self):
        login(self.client, self.admin, self.org)
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, reverse("academy:order_detail", args=[self.order.pk]))
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.transaction_ref), (Order.Status.PAID, "VIR-2026-11-0042"))
        entry = self.order.audit_log.get(action=OrderAudit.Action.PAYMENT_VERIFIED)
        self.assertEqual(
            (entry.actor, entry.amount, entry.currency, entry.reference, entry.old_status, entry.new_status),
            (self.admin, Decimal("29.00"), "USD", "VIR-2026-11-0042", Order.Status.AWAITING_PAYMENT, Order.Status.PAID),
        )
        self.assertEqual(entry.notes, "Virement lu sur le relevé du 11/11.")
        self.assertIsNotNone(entry.created_at)
        log = AuditLog.objects.get(action="academy_payment_confirmed", target_id=str(self.order.pk))
        self.assertEqual((log.actor, log.summary["amount"], log.summary["currency"]), (self.admin, "29.00", "USD"))
        self.assertTrue(can_access_resource(self.buyer, self.complete_res))
        self.assertFalse(can_access_resource(self.buyer, self.guided_res))

    def test_repeated_confirmation_creates_no_duplicate(self):
        login(self.client, self.admin, self.org)
        self.client.post(self.url, self.data)
        self.client.post(self.url, self.data)
        _, confirmed = services.confirm_payment(request=fake_request(self.admin, self.org), order=self.order, note="encore")
        self.assertFalse(confirmed)
        self.assertEqual(self.order.audit_log.filter(action=OrderAudit.Action.PAYMENT_VERIFIED).count(), 1)
        self.assertEqual(Enrollment.objects.filter(order=self.order).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="academy_payment_confirmed").count(), 1)

    def test_note_and_receipt_check_are_required(self):
        login(self.client, self.admin, self.org)
        for missing in ("confirm-note", "confirm-received"):
            with self.subTest(missing=missing):
                data = {k: v for k, v in self.data.items() if k != missing}
                self.assertEqual(self.client.post(self.url, data).status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.AWAITING_PAYMENT)
        with self.assertRaises(ValidationError):
            services.confirm_payment(request=fake_request(self.admin, self.org), order=self.order, note="  ")

    def test_database_refuses_a_payment_without_history(self):
        with self.assertRaises(DatabaseError), transaction.atomic():
            Order.objects.create(organization=self.org, user=self.buyer, offer=self.complete, status=Order.Status.PAID)
        with self.assertRaises(DatabaseError), transaction.atomic():
            Order.objects.filter(pk=self.order.pk).update(status=Order.Status.PAID)


class RefundTests(PublishedOfferMixin, AcademyTestCase):
    """D2 et D6 : remboursement intégral et partiel."""

    def setUp(self):
        super().setUp()
        self.publish()
        self.request = fake_request(self.admin, self.org)
        self.order, self.enrollment = self.buy(self.complete)
        lesson = Lesson.objects.create(
            course=Course.objects.create(program=self.program, title_fr="Comprendre", title_en="Understand"),
            title_fr="Leçon", title_en="Lesson",
        )
        self.progress = LessonProgress.objects.create(enrollment=self.enrollment, lesson=lesson, completed_at=timezone.now())

    def test_full_refund_removes_access_immediately_and_keeps_everything(self):
        self.assertTrue(can_access_resource(self.buyer, self.complete_res))
        services.refund(request=self.request, order=self.order, amount="29.00", reason="Demande dans le délai.", reference="RB-1")
        self.order.refresh_from_db()
        self.enrollment.refresh_from_db()
        self.assertEqual((self.order.status, self.order.refunded_amount), (Order.Status.REFUNDED, Decimal("29.00")))
        self.assertFalse(can_access_resource(self.buyer, self.complete_res))
        self.assertEqual(self.enrollment.status, Enrollment.Status.CANCELLED)
        self.assertTrue(LessonProgress.objects.filter(pk=self.progress.pk, completed_at__isnull=False).exists())
        entry = self.order.audit_log.get(action=OrderAudit.Action.REFUNDED)
        self.assertEqual((entry.actor, entry.amount, entry.currency, entry.notes, entry.reference),
                         (self.admin, Decimal("29.00"), "USD", "Demande dans le délai.", "RB-1"))
        self.assertEqual(self.order.audit_log.count(), 2, "confirmation et remboursement sont conservés")

    def test_rights_cannot_be_reactivated_after_a_full_refund(self):
        services.refund(request=self.request, order=self.order, amount="29.00", reason="Remboursé")
        with self.assertRaises(ValidationError):
            services.confirm_payment(request=self.request, order=self.order, note="erreur")
        with self.assertRaises(DatabaseError), transaction.atomic():
            Enrollment.objects.filter(pk=self.enrollment.pk).update(status=Enrollment.Status.ACTIVE)
        for status in (Order.Status.PAID, Order.Status.AWAITING_PAYMENT):
            with self.subTest(status=status), self.assertRaises(DatabaseError), transaction.atomic():
                Order.objects.filter(pk=self.order.pk).update(status=status)

    def test_partial_refund_keeps_access_and_is_recorded(self):
        services.refund(request=self.request, order=self.order, amount="10.00", reason="Geste partiel")
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.refunded_amount), (Order.Status.PAID, Decimal("10.00")))
        self.assertTrue(self.order.has_partial_refund)
        self.assertTrue(can_access_resource(self.buyer, self.complete_res))
        self.assertEqual(self.order.audit_log.filter(action=OrderAudit.Action.PARTIAL_REFUND).get().amount, Decimal("10.00"))
        # Le solde rembourse intégralement la commande.
        services.refund(request=self.request, order=self.order, amount="19.00", reason="Solde")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.REFUNDED)
        self.assertFalse(can_access_resource(self.buyer, self.complete_res))

    def test_refund_limits(self):
        for amount in ("0", "-1", "29.01", "abc"):
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                services.refund(request=self.request, order=self.order, amount=amount, reason="x")
        with self.assertRaises(ValidationError):
            services.refund(request=self.request, order=self.order, amount="5", reason=" ")
        student = make_user(self.org, R.ACADEMY_STUDENT)
        with self.assertRaises(PermissionDenied):
            services.refund(request=fake_request(student, self.org), order=self.order, amount="5", reason="x")
        with self.assertRaises(DatabaseError), transaction.atomic():
            Order.objects.filter(pk=self.order.pk).update(refunded_amount=Decimal("5"))

    def test_refund_page_records_a_full_refund(self):
        login(self.client, self.admin, self.org)
        url = reverse("academy:order_refund", args=[self.order.pk])
        self.assertEqual(self.client.post(url, {"refund-amount": "30", "refund-reason": "x"}).status_code, 400)
        response = self.client.post(url, {"refund-amount": "29.00", "refund-reason": "Rétractation"})
        self.assertRedirects(response, reverse("academy:order_detail", args=[self.order.pk]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.REFUNDED)


class BuyerJourneyTests(PublishedOfferMixin, AcademyTestCase):
    def test_draft_offer_or_unpublished_programme_cannot_be_ordered(self):
        login(self.client, self.buyer, self.org)
        self.assertEqual(self.client.get(reverse("academy:offer_detail", args=[self.complete.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("academy:order_create", args=[self.complete.pk]), {"acknowledge": "on"}).status_code, 404)
        ProgramOffer.objects.filter(pk=self.complete.pk).update(status=ProgramOffer.Status.PUBLISHED)
        self.assertEqual(self.client.get(reverse("academy:offer_detail", args=[self.complete.pk])).status_code, 404, "programme non publié")
        with self.assertRaises(ValidationError):
            services.place_order(request=fake_request(self.buyer, self.org), offer=self.complete)
        self.assertFalse(Order.objects.exists())

    def test_order_needs_the_notice_and_is_not_duplicated(self):
        self.publish()
        login(self.client, self.buyer, self.org)
        url = reverse("academy:order_create", args=[self.complete.pk])
        self.assertEqual(self.client.post(url, {}).status_code, 400)
        self.assertFalse(Order.objects.exists())
        response = self.client.post(url, {"acknowledge": "on"})
        order = Order.objects.get()
        self.assertRedirects(response, reverse("academy:my_order_detail", args=[order.pk]))
        self.assertEqual((order.status, order.price, order.currency), (Order.Status.AWAITING_PAYMENT, Decimal("29.00"), "USD"))
        self.assertEqual((order.risk_notice_version, order.terms_version), (settings.SYSTEMC_RISK_NOTICE_VERSION, ""))
        self.client.post(url, {"acknowledge": "on"})
        self.assertEqual(Order.objects.count(), 1)
        page = self.client.get(reverse("academy:my_order_detail", args=[order.pk]))
        self.assertContains(page, "29,00")
        self.assertFalse(can_access_resource(self.buyer, self.complete_res))

    def test_offer_pages_show_the_risk_notice_and_real_availability(self):
        self.publish()
        self.resource("Guide à venir", offers=[self.complete], status=Resource.Status.DRAFT)
        login(self.client, self.buyer, self.org)
        for url in (reverse("academy:offer_list"), reverse("academy:offer_detail", args=[self.complete.pk])):
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), "Aucun résultat financier n'est garanti")
        page = self.client.get(reverse("academy:offer_detail", args=[self.complete.pk]))
        self.assertContains(page, "En préparation")
        self.assertNotContains(page, "Support d&#x27;atelier", msg_prefix="ressource réservée à Guided")

    def test_buyer_sees_and_cancels_only_own_orders(self):
        self.publish()
        order, _ = services.place_order(request=fake_request(self.buyer, self.org), offer=self.complete)
        other = make_user(self.org, R.ACADEMY_STUDENT)
        login(self.client, other, self.org)
        self.assertEqual(self.client.get(reverse("academy:my_order_detail", args=[order.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("academy:my_order_cancel", args=[order.pk])).status_code, 404)
        login(self.client, self.buyer, self.org)
        self.client.post(reverse("academy:my_order_cancel", args=[order.pk]), {"cancel-reason": ""})
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(order.audit_log.get(action=OrderAudit.Action.CANCELLED).actor, self.buyer)

    def test_paid_order_cannot_be_cancelled(self):
        self.publish()
        order, _ = self.buy(self.complete)
        with self.assertRaises(ValidationError):
            services.cancel_order(request=fake_request(self.buyer, self.org), order=order)
        with self.assertRaises(ValidationError):
            services.cancel_order(request=fake_request(self.admin, self.org), order=order, reason="x")

    def test_offers_of_another_organization_are_invisible(self):
        self.publish()
        other = make_org()
        stranger = make_user(other, R.ACADEMY_STUDENT)
        login(self.client, stranger, other)
        self.assertEqual(self.client.get(reverse("academy:offer_detail", args=[self.complete.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("academy:offer_list")), f'href="{reverse("academy:offer_detail", args=[self.complete.pk])}"')


class OrderAdminPageTests(PublishedOfferMixin, AcademyTestCase):
    def test_order_list_is_scoped_and_restricted(self):
        self.publish()
        services.place_order(request=fake_request(self.buyer, self.org), offer=self.complete)
        other = make_org()
        program_b = Program.objects.create(organization=other, title_fr="B", title_en="B", is_published=True)
        offer_b = ProgramOffer.objects.create(program=program_b, slug="b", name_fr="Offre étrangère", name_en="Foreign", price=Decimal("1"), status="published")
        foreign_buyer = make_user(other, R.ACADEMY_STUDENT, email="etranger@example.org")
        services.place_order(request=fake_request(foreign_buyer, other), offer=offer_b)
        login(self.client, self.admin, self.org)
        page = self.client.get(reverse("academy:order_list"))
        self.assertContains(page, self.buyer.email)
        self.assertNotContains(page, "etranger@example.org")
        self.assertContains(self.client.get(reverse("academy:order_list") + "?status=awaiting_payment"), self.buyer.email)
        login(self.client, self.buyer, self.org)
        self.assertEqual(self.client.get(reverse("academy:order_list")).status_code, 403)


class LessonUniquenessTests(AcademyTestCase):
    @staticmethod
    def checked(create):
        """Les contraintes de position sont différées : on force leur vérification immédiate."""
        with transaction.atomic():
            create()
            with connection.cursor() as cursor:
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")

    def test_no_duplicate_lesson_in_a_step(self):
        course = Course.objects.create(program=self.program, title_fr="Comprendre", title_en="Understand", position=1)
        Lesson.objects.create(course=course, title_fr="A", title_en="A", position=1)
        cases = {
            "même position": lambda: Lesson.objects.create(course=course, title_fr="B", title_en="B", position=1),
            "même titre": lambda: Lesson.objects.create(course=course, title_fr="A", title_en="A", position=2),
            "même étape": lambda: Course.objects.create(program=self.program, title_fr="Doublon", title_en="Duplicate", position=1),
        }
        for label, create in cases.items():
            with self.subTest(label), self.assertRaises(IntegrityError):
                self.checked(create)


class AcademyDemoCommandTests(TestCase):
    def test_refused_outside_debug(self):
        org = make_org()
        with self.assertRaises(CommandError):
            call_command("seed_academy_demo", organization=org.slug, yes=True, stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_creates_only_labelled_demo_data(self):
        org = make_org()
        call_command("seed_academy_demo", organization=org.slug, yes=True, stdout=StringIO())
        offer = ProgramOffer.objects.get(program__organization=org)
        self.assertTrue(offer.name_fr.startswith("[Démo]") and offer.program.title_fr.startswith("[Démo]"))
        self.assertEqual(offer.status, ProgramOffer.Status.PUBLISHED)
        self.assertFalse(Order.objects.exists(), "aucune commande ni aucun paiement simulé")
        self.assertTrue(all(r.external_url.startswith("https://example.org/") for r in Resource.objects.all()))



def demo_program(org, **extra):
    return Program.objects.create(
        organization=org, title_fr="[Démo] Essai", title_en="[Demo] Trial", is_published=True, is_demo=True, **extra
    )


class SelfConfirmationTests(PublishedOfferMixin, AcademyTestCase):
    """Personne ne confirme le paiement de sa propre commande, sauf démonstration en DEBUG."""

    def test_buyer_cannot_confirm_own_real_order(self):
        self.publish()
        request = fake_request(self.admin, self.org)
        order, _ = services.place_order(request=request, offer=self.complete)
        with self.assertRaises(ValidationError):
            services.confirm_payment(request=request, order=order, note="Je me confirme")
        login(self.client, self.admin, self.org)
        url = reverse("academy:order_confirm", args=[order.pk])
        self.client.post(url, {"confirm-received": "on", "confirm-note": "Je me confirme"})
        page = self.client.get(reverse("academy:order_detail", args=[order.pk]))
        self.assertContains(page, "Vous ne pouvez pas confirmer le paiement de votre propre commande")
        self.assertNotContains(page, 'action="%s"' % url)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.AWAITING_PAYMENT)
        with override_settings(DEBUG=True), self.assertRaises(ValidationError):
            services.confirm_payment(request=request, order=order, note="Même en DEBUG")
        # La base refuse aussi, même sans passer par le service.
        with self.assertRaises(DatabaseError), transaction.atomic():
            OrderAudit.objects.create(
                order=order, action=OrderAudit.Action.PAYMENT_VERIFIED, old_status=order.status, new_status="paid",
                actor=self.admin, notes="contournement", amount=order.price, currency=order.currency,
            )

    def test_another_admin_can_confirm(self):
        self.publish()
        order, _ = services.place_order(request=fake_request(self.admin, self.org), offer=self.complete)
        second_admin = make_user(self.org, R.ORG_ADMIN)
        order, confirmed = services.confirm_payment(request=fake_request(second_admin, self.org), order=order, note="Vérifié")
        self.assertTrue(confirmed)
        self.assertEqual(order.audit_log.get(action=OrderAudit.Action.PAYMENT_VERIFIED).actor, second_admin)

    def test_demo_order_self_confirmation_only_in_debug(self):
        program = demo_program(self.org)
        offer = ProgramOffer.objects.create(program=program, slug="demo", name_fr="[Démo] Offre", name_en="[Demo] Offer",
                                            price=Decimal("5"), status=ProgramOffer.Status.PUBLISHED)
        request = fake_request(self.admin, self.org)
        with override_settings(DEBUG=True):
            order, _ = services.place_order(request=request, offer=offer)
        with self.assertRaises(ValidationError):
            services.confirm_payment(request=request, order=order, note="hors DEBUG")
        with override_settings(DEBUG=True):
            order, confirmed = services.confirm_payment(request=request, order=order, note="Essai local")
        self.assertTrue(confirmed)
        self.assertEqual(order.status, Order.Status.PAID)


class DemoDataTests(PublishedOfferMixin, AcademyTestCase):
    def test_demo_label_and_flag_go_together(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Program.objects.create(organization=self.org, title_fr="[Démo] Faux", title_en="x")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Program.objects.create(organization=self.org, title_fr="Vrai programme", title_en="x", is_demo=True)
        with self.assertRaises(DatabaseError), transaction.atomic():
            Program.objects.filter(pk=self.program.pk).update(is_demo=True, title_fr="[Démo] SYSTEM-C Method")

    def test_demo_offer_is_not_purchasable_outside_debug(self):
        program = demo_program(self.org)
        offer = ProgramOffer.objects.create(program=program, slug="demo", name_fr="[Démo] Offre", name_en="[Demo] Offer",
                                            price=Decimal("5"), status=ProgramOffer.Status.PUBLISHED)
        self.assertFalse(services.purchasable_offers(self.org).filter(pk=offer.pk).exists())
        with self.assertRaises(ValidationError):
            services.place_order(request=fake_request(self.buyer, self.org), offer=offer)
        login(self.client, self.buyer, self.org)
        self.assertEqual(self.client.get(reverse("academy:offer_detail", args=[offer.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("academy:offer_list")), "[Démo]")
        with override_settings(DEBUG=True):
            self.assertTrue(services.purchasable_offers(self.org).filter(pk=offer.pk).exists())

    @override_settings(DEBUG=True)
    def test_demo_seed_labels_everything_and_leaves_real_data_untouched(self):
        self.publish()
        call_command("seed_system_c_method", organization=self.org.slug, yes=True, stdout=StringIO())
        order, _ = self.buy(self.complete)
        snapshot = lambda: (  # noqa: E731
            list(ProgramOffer.objects.order_by("pk").values()),
            list(Order.objects.order_by("pk").values()),
            list(Resource.objects.order_by("pk").values("pk", "title_fr", "status", "updated_at")),
            list(Program.objects.order_by("pk").values()),
        )
        before = snapshot()
        call_command("seed_academy_demo", organization=self.org.slug, yes=True, stdout=StringIO())
        after = snapshot()
        self.assertEqual(after[0][: len(before[0])], before[0])
        self.assertEqual(after[1], before[1], "aucune commande créée ni modifiée")
        self.assertEqual(after[2][: len(before[2])], before[2])
        demo = Program.objects.get(is_demo=True)
        self.assertTrue(demo.title_fr.startswith("[Démo]"))
        self.assertTrue(all(o.name_fr.startswith("[Démo]") for o in demo.offers.all()))
        self.assertTrue(all(r.title_fr.startswith("[Démo]") for r in demo.resources.all()))
        self.assertEqual(Program.objects.filter(is_demo=False).count(), len(before[3]))


class AccessDurationTests(PublishedOfferMixin, AcademyTestCase):
    def test_default_access_has_explicitly_no_expiry(self):
        self.assertEqual(self.complete.access_mode, AccessMode.PERMANENT)
        _, enrollment = self.buy(self.complete)
        self.assertEqual((enrollment.access_mode, enrollment.access_until), (AccessMode.PERMANENT, None))
        self.assertTrue(enrollment.is_access_valid())
        self.publish()
        login(self.client, self.buyer, self.org)
        page = self.client.get(reverse("academy:offer_detail", args=[self.complete.pk]))
        self.assertContains(page, "sans date d'expiration")
        self.assertContains(page, "ne sont pas inclus")

    def test_limited_offer_sets_an_end_date(self):
        ProgramOffer.objects.filter(pk=self.guided.pk).update(access_mode=AccessMode.LIMITED, access_days=28)
        self.guided.refresh_from_db()
        before = timezone.now()
        _, enrollment = self.buy(self.guided)
        self.assertEqual(enrollment.access_mode, AccessMode.LIMITED)
        self.assertTrue(before + timedelta(days=28) <= enrollment.access_until <= timezone.now() + timedelta(days=28))
        Enrollment.objects.filter(pk=enrollment.pk).update(access_until=timezone.now() - timedelta(seconds=1))
        self.assertFalse(can_access_resource(self.buyer, self.guided_res))

    def test_access_mode_must_be_consistent(self):
        for fields in ({"access_mode": AccessMode.LIMITED, "access_days": None},
                       {"access_mode": AccessMode.PERMANENT, "access_days": 30},
                       {"access_mode": AccessMode.LIMITED, "access_days": 0}):
            with self.subTest(fields=fields), self.assertRaises(IntegrityError), transaction.atomic():
                ProgramOffer.objects.filter(pk=self.complete.pk).update(**fields)
        _, enrollment = self.buy(self.complete)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Enrollment.objects.filter(pk=enrollment.pk).update(access_until=timezone.now())


class PartialRefundAndRevocationTests(PublishedOfferMixin, AcademyTestCase):
    def setUp(self):
        super().setUp()
        self.publish()
        self.request = fake_request(self.admin, self.org)
        self.order, self.enrollment = self.buy(self.complete)

    def test_cumulative_refunds_never_exceed_the_amount_paid(self):
        services.refund(request=self.request, order=self.order, amount="10.00", reason="Premier geste")
        services.refund(request=self.request, order=self.order, amount="10.00", reason="Second geste")
        with self.assertRaises(ValidationError):
            services.refund(request=self.request, order=self.order, amount="9.01", reason="Trop")
        self.order.refresh_from_db()
        self.assertEqual((self.order.refunded_amount, self.order.status), (Decimal("20.00"), Order.Status.PAID))
        form = RefundForm({"refund-amount": "9.01", "refund-reason": "x"}, order=self.order)
        self.assertFalse(form.is_valid())
        with self.assertRaises(IntegrityError), transaction.atomic():
            Order.objects.filter(pk=self.order.pk).update(refunded_amount=Decimal("29.01"))

    def test_partial_refund_alone_keeps_access(self):
        services.refund(request=self.request, order=self.order, amount="5.00", reason="Geste")
        self.assertTrue(can_access_resource(self.buyer, self.complete_res))

    def test_revocation_is_separate_authorised_motivated_and_audited(self):
        with self.assertRaises(ValidationError):
            services.revoke_access(request=self.request, order=self.order, reason="Sans remboursement partiel")
        services.refund(request=self.request, order=self.order, amount="5.00", reason="Geste")
        student = make_user(self.org, R.ACADEMY_STUDENT)
        crm_admin = make_user(self.org, R.CRM_ADMIN)
        for user in (student, crm_admin):
            with self.subTest(role=user), self.assertRaises(PermissionDenied):
                services.revoke_access(request=fake_request(user, self.org), order=self.order, reason="x")
        with self.assertRaises(ValidationError):
            services.revoke_access(request=self.request, order=self.order, reason=" ")
        login(self.client, self.admin, self.org)
        response = self.client.post(reverse("academy:order_revoke", args=[self.order.pk]), {"revoke-reason": "Décision après réclamation"})
        self.assertRedirects(response, reverse("academy:order_detail", args=[self.order.pk]))
        self.enrollment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual((self.enrollment.status, self.order.status), (Enrollment.Status.REVOKED, Order.Status.PAID))
        self.assertFalse(can_access_resource(self.buyer, self.complete_res))
        entry = self.order.audit_log.get(action=OrderAudit.Action.ACCESS_REVOKED)
        self.assertEqual((entry.actor, entry.notes), (self.admin, "Décision après réclamation"))
        self.assertTrue(AuditLog.objects.filter(action="academy_access_revoked", target_id=str(self.order.pk)).exists())
        # Répéter ne crée rien ; l'accès ne peut pas être rouvert.
        services.revoke_access(request=self.request, order=self.order, reason="encore")
        self.assertEqual(self.order.audit_log.filter(action=OrderAudit.Action.ACCESS_REVOKED).count(), 1)
        with self.assertRaises(DatabaseError), transaction.atomic():
            Enrollment.objects.filter(pk=self.enrollment.pk).update(status=Enrollment.Status.ACTIVE)

    def test_revocation_is_refused_from_another_organization(self):
        services.refund(request=self.request, order=self.order, amount="5.00", reason="Geste")
        other = make_org()
        foreign_admin = make_user(other, R.ORG_ADMIN)
        with self.assertRaises(PermissionDenied):
            services.revoke_access(request=fake_request(foreign_admin, other), order=self.order, reason="x")
        login(self.client, foreign_admin, other)
        self.assertEqual(self.client.post(reverse("academy:order_revoke", args=[self.order.pk]), {"revoke-reason": "x"}).status_code, 404)


class MockupDashboardAcademyTests(PublishedOfferMixin, AcademyTestCase):
    """Commandes sur le tableau de bord, la cloche et la recherche : réservées à payments.view_orders."""

    def setUp(self):
        super().setUp()
        self.publish()
        self.order = Order.objects.create(organization=self.org, user=self.buyer, offer=self.complete, status=Order.Status.AWAITING_PAYMENT)

    def test_org_admin_sees_orders_kpi_priority_and_bell(self):
        login(self.client, self.admin, self.org)
        context = self.client.get(reverse("core:dashboard")).context
        self.assertEqual(next(k for k in context["kpis"] if k["rank"] == 40)["value"], 1)
        self.assertEqual(next(p for p in context["priorities"] if p["rank"] == 15)["count"], 1)
        self.assertIn(1, [item["count"] for item in context["notifications"] if item["rank"] == 15])
        groups = self.client.get(reverse("core:search"), {"q": f"#{self.order.pk}"}).context["groups"]
        self.assertIn(reverse("academy:order_detail", args=[self.order.pk]), [r["url"] for g in groups for r in g["results"]])

    def test_other_roles_see_no_order(self):
        for role in (R.CRM_ADMIN, R.ACADEMY_STUDENT):
            with self.subTest(role=role):
                user = make_user(self.org, role)
                login(self.client, user, self.org)
                response = self.client.get(reverse("core:search"), {"q": self.buyer.email})
                self.assertNotIn("Commandes", [g["title"] for g in response.context["groups"]])
                self.assertEqual(response.context["notifications_total"], 0)

    def test_orders_of_another_organization_are_not_counted(self):
        other = make_org()
        program = Program.objects.create(organization=other, title_fr="Autre", title_en="Other")
        Order.objects.create(organization=other, user=make_user(other, R.ACADEMY_STUDENT),
                             offer=self.offer("x", "1.00", program=program), status=Order.Status.AWAITING_PAYMENT)
        login(self.client, self.admin, self.org)
        context = self.client.get(reverse("core:dashboard")).context
        self.assertEqual(next(k for k in context["kpis"] if k["rank"] == 40)["value"], 1)
