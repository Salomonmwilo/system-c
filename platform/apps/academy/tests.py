"""Tests for Academy app (SYSTEM-C Method)."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.academy.models import (
    Enrollment,
    Lesson,
    LessonProgress,
    Order,
    OrderAudit,
    Program,
    ProgramOffer,
    Resource,
)
from apps.core.models import Organization, User


class AcademyModelsTestCase(TestCase):
    """Test Academy models for SYSTEM-C Method."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
        )
        cls.user = User.objects.create_user(
            email="learner@example.com",
            password="testpass123",
            full_name="Test Learner",
        )
        cls.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
            full_name="Admin User",
            is_staff=True,
        )

    def setUp(self):
        """Set up test instance."""
        self.program = Program.objects.create(
            organization=self.org,
            title_fr="Test Program",
            title_en="Test Program",
        )

    def test_program_creation(self):
        """Test program creation and properties."""
        self.assertEqual(self.program.title, "Test Program")
        self.assertEqual(self.program.organization, self.org)
        self.assertFalse(self.program.is_published)

    def test_program_offer_creation(self):
        """Test offer creation."""
        offer = ProgramOffer.objects.create(
            program=self.program,
            slug="complete",
            name_fr="Complete",
            name_en="Complete",
            price_usd=Decimal("29.00"),
        )
        self.assertEqual(offer.program, self.program)
        self.assertEqual(offer.price_usd, Decimal("29.00"))
        self.assertEqual(offer.status, ProgramOffer.Status.DRAFT)
        self.assertEqual(offer.name, "Complete")

    def test_program_offer_unique_slug(self):
        """Test offer slug uniqueness per program."""
        ProgramOffer.objects.create(
            program=self.program,
            slug="complete",
            name_fr="Complete",
            name_en="Complete",
            price_usd=Decimal("29.00"),
        )
        # Should not allow duplicate slug for same program
        with self.assertRaises(Exception):  # IntegrityError
            ProgramOffer.objects.create(
                program=self.program,
                slug="complete",
                name_fr="Complete 2",
                name_en="Complete 2",
                price_usd=Decimal("39.00"),
            )

    def test_resource_creation(self):
        """Test resource creation."""
        resource = Resource.objects.create(
            program=self.program,
            title_fr="Guide",
            title_en="Guide",
            resource_type=Resource.ResourceType.GUIDE,
        )
        self.assertEqual(resource.program, self.program)
        self.assertEqual(resource.resource_type, Resource.ResourceType.GUIDE)
        self.assertEqual(resource.status, Resource.Status.DRAFT)
        self.assertEqual(resource.title, "Guide")

    def test_order_creation(self):
        """Test order creation."""
        offer = ProgramOffer.objects.create(
            program=self.program,
            slug="complete",
            name_fr="Complete",
            name_en="Complete",
            price_usd=Decimal("29.00"),
        )
        order = Order.objects.create(
            organization=self.org,
            user=self.user,
            offer=offer,
            price_usd=Decimal("29.00"),
        )
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.offer, offer)
        self.assertEqual(order.status, Order.Status.DRAFT)
        self.assertEqual(order.price_usd, Decimal("29.00"))

    def test_order_status_transitions(self):
        """Test valid order status transitions."""
        offer = ProgramOffer.objects.create(
            program=self.program,
            slug="complete",
            name_fr="Complete",
            name_en="Complete",
            price_usd=Decimal("29.00"),
        )
        order = Order.objects.create(
            organization=self.org,
            user=self.user,
            offer=offer,
            price_usd=Decimal("29.00"),
        )

        # Simulate payment workflow
        order.status = Order.Status.AWAITING_PAYMENT
        order.save()
        self.assertEqual(order.status, Order.Status.AWAITING_PAYMENT)

        order.status = Order.Status.PAYMENT_PENDING
        order.save()
        self.assertEqual(order.status, Order.Status.PAYMENT_PENDING)

        order.status = Order.Status.PAID
        order.save()
        self.assertEqual(order.status, Order.Status.PAID)

    def test_order_audit_tracking(self):
        """Test order audit trail."""
        offer = ProgramOffer.objects.create(
            program=self.program,
            slug="complete",
            name_fr="Complete",
            name_en="Complete",
            price_usd=Decimal("29.00"),
        )
        order = Order.objects.create(
            organization=self.org,
            user=self.user,
            offer=offer,
            price_usd=Decimal("29.00"),
        )

        # Create audit record
        audit = OrderAudit.objects.create(
            order=order,
            action=OrderAudit.Action.STATUS_CHANGED,
            old_status=Order.Status.DRAFT,
            new_status=Order.Status.PAYMENT_PENDING,
            user=self.admin_user,
        )
        self.assertEqual(audit.order, order)
        self.assertEqual(audit.action, OrderAudit.Action.STATUS_CHANGED)

    def test_enrollment_with_offer(self):
        """Test enrollment linked to offer and order."""
        offer = ProgramOffer.objects.create(
            program=self.program,
            slug="complete",
            name_fr="Complete",
            name_en="Complete",
            price_usd=Decimal("29.00"),
        )
        order = Order.objects.create(
            organization=self.org,
            user=self.user,
            offer=offer,
            price_usd=Decimal("29.00"),
            status=Order.Status.PAID,
        )
        enrollment = Enrollment.objects.create(
            organization=self.org,
            program=self.program,
            user=self.user,
            offer=offer,
            order=order,
            status=Enrollment.Status.ACTIVE,
            access_until=timezone.now() + timedelta(days=90),
        )
        self.assertEqual(enrollment.offer, offer)
        self.assertEqual(enrollment.order, order)
        self.assertTrue(enrollment.is_access_valid())

    def test_enrollment_access_expiration(self):
        """Test enrollment access expiration."""
        offer = ProgramOffer.objects.create(
            program=self.program,
            slug="complete",
            name_fr="Complete",
            name_en="Complete",
            price_usd=Decimal("29.00"),
        )
        # Create enrollment with expired access
        enrollment = Enrollment.objects.create(
            organization=self.org,
            program=self.program,
            user=self.user,
            offer=offer,
            status=Enrollment.Status.ACTIVE,
            access_until=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(enrollment.is_access_valid())

    def test_enrollment_access_check_status(self):
        """Test that suspended enrollment blocks access even if date is valid."""
        offer = ProgramOffer.objects.create(
            program=self.program,
            slug="complete",
            name_fr="Complete",
            name_en="Complete",
            price_usd=Decimal("29.00"),
        )
        enrollment = Enrollment.objects.create(
            organization=self.org,
            program=self.program,
            user=self.user,
            offer=offer,
            status=Enrollment.Status.SUSPENDED,
            access_until=timezone.now() + timedelta(days=90),
        )
        self.assertFalse(enrollment.is_access_valid())

    def test_lesson_progress_tracking(self):
        """Test lesson progress tracking."""
        # Create course and lesson
        from apps.academy.models import Course

        course = Course.objects.create(
            program=self.program,
            title_fr="Course 1",
            title_en="Course 1",
        )
        lesson = Lesson.objects.create(
            course=course,
            title_fr="Lesson 1",
            title_en="Lesson 1",
        )

        # Create enrollment
        enrollment = Enrollment.objects.create(
            organization=self.org,
            program=self.program,
            user=self.user,
            status=Enrollment.Status.ACTIVE,
        )

        # Track progress
        progress = LessonProgress.objects.create(
            enrollment=enrollment,
            lesson=lesson,
        )
        self.assertFalse(progress.is_completed())

        # Mark as completed
        progress.completed_at = timezone.now()
        progress.save()
        self.assertTrue(progress.is_completed())

    def test_bilingual_offer_name(self):
        """Test bilingual offer name selection."""
        offer = ProgramOffer.objects.create(
            program=self.program,
            slug="complete",
            name_fr="Complet",
            name_en="Complete",
            price_usd=Decimal("29.00"),
        )
        # Both FR and EN exist, property should return based on language
        self.assertEqual(offer.name_fr, "Complet")
        self.assertEqual(offer.name_en, "Complete")

    def test_resource_bilingual_title(self):
        """Test bilingual resource title."""
        resource = Resource.objects.create(
            program=self.program,
            title_fr="Guide",
            title_en="Guide",
            resource_type=Resource.ResourceType.GUIDE,
        )
        self.assertEqual(resource.title_fr, "Guide")
        self.assertEqual(resource.title_en, "Guide")

    def test_organization_isolation(self):
        """Test that orders are isolated by organization."""
        other_org = Organization.objects.create(
            name="Other Org",
            slug="other-org",
        )
        offer = ProgramOffer.objects.create(
            program=self.program,
            slug="complete",
            name_fr="Complete",
            name_en="Complete",
            price_usd=Decimal("29.00"),
        )
        order1 = Order.objects.create(
            organization=self.org,
            user=self.user,
            offer=offer,
            price_usd=Decimal("29.00"),
        )

        # Orders from different org should be separate
        other_orders = Order.objects.filter(organization=other_org)
        self.assertEqual(other_orders.count(), 0)
        self.assertEqual(order1.organization, self.org)
