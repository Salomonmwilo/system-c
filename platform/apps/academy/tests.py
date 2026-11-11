"""Tests du module academy (SYSTEM-C Method) : droits d'accès, intégrité, fichiers privés, isolation."""

import tempfile
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.academy.access import active_enrollments, can_access_resource
from apps.academy.models import (
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
from apps.core.testing import login, make_org, make_user
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
        user = user or self.buyer
        order = Order.objects.create(organization=offer.program.organization, user=user, offer=offer, status=status)
        enrollment = Enrollment.objects.create(
            organization=offer.program.organization,
            program=offer.program,
            user=user,
            offer=offer,
            order=order,
            status=Enrollment.Status.ACTIVE,
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
        for status in (Order.Status.CANCELLED, Order.Status.REFUNDED):
            with self.subTest(status=status):
                user = make_user(self.org, R.ACADEMY_STUDENT)
                order, enrollment = self.buy(self.complete, user=user)
                self.assertTrue(can_access_resource(user, self.complete_res))
                order.status = status
                order.save()
                enrollment.refresh_from_db()
                self.assertFalse(enrollment.is_access_valid())
                self.assertFalse(can_access_resource(user, self.complete_res))
                # L'historique d'inscription reste en place.
                self.assertTrue(Enrollment.objects.filter(pk=enrollment.pk, order=order).exists())

    def test_expired_or_suspended_enrollment_gives_no_access(self):
        _, enrollment = self.buy(self.complete)
        enrollment.access_until = timezone.now() - timedelta(minutes=1)
        enrollment.save()
        self.assertFalse(can_access_resource(self.buyer, self.complete_res))
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
        entry = OrderAudit.objects.create(
            order=order,
            action=OrderAudit.Action.PAYMENT_VERIFIED,
            old_status=Order.Status.PAYMENT_PENDING,
            new_status=Order.Status.PAID,
            actor=self.admin,
            reference="PSP-2026-0001",
            notes="Virement vérifié sur le relevé.",
        )
        self.assertEqual((entry.actor, entry.reference), (self.admin, "PSP-2026-0001"))
        with self.assertRaises(PermissionError):
            entry.save()
        with self.assertRaises(PermissionError):
            entry.delete()
        with self.assertRaises(DatabaseError), transaction.atomic():
            OrderAudit.objects.filter(pk=entry.pk).update(notes="réécrit")
        with self.assertRaises(DatabaseError), transaction.atomic():
            OrderAudit.objects.filter(pk=entry.pk).delete()

    def test_enrollment_must_match_its_order(self):
        order = Order.objects.create(organization=self.org, user=self.buyer, offer=self.complete, status=Order.Status.PAID)
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
