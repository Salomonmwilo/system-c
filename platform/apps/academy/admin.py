"""Django admin for Academy app."""

from django.contrib import admin
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from .models import Course, Enrollment, Lesson, LessonProgress, Order, OrderAudit, Program, ProgramOffer, Resource


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("title_fr", "organization", "is_published", "created_at")
    list_filter = ("is_published", "organization", "created_at")
    search_fields = ("title_fr", "title_en")
    readonly_fields = ("id", "created_at")
    fieldsets = (
        (None, {"fields": ("id", "organization", "title_fr", "title_en")}),
        (_("Description"), {"fields": ("description_fr", "description_en")}),
        (_("Status"), {"fields": ("is_published", "created_at")}),
    )


class LessonInline(admin.TabularInline):
    model = Lesson
    fields = ("position", "title_fr", "title_en")
    ordering = ("position",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title_fr", "program", "position", "lesson_count")
    list_filter = ("program",)
    search_fields = ("title_fr", "title_en", "program__title_fr")
    ordering = ("program", "position")
    inlines = [LessonInline]
    fields = ("program", "position", "title_fr", "title_en")

    def lesson_count(self, obj):
        return obj.lessons.count()

    lesson_count.short_description = _("Lessons")


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title_fr", "course", "position")
    list_filter = ("course__program",)
    search_fields = ("title_fr", "title_en")
    ordering = ("course", "position")
    fieldsets = (
        (None, {"fields": ("course", "position", "title_fr", "title_en")}),
        (_("Content"), {"fields": ("body_fr", "body_en")}),
    )


class ProgramOfferInline(admin.TabularInline):
    model = ProgramOffer
    fields = ("slug", "name_fr", "price_usd", "status", "position")
    ordering = ("position",)


@admin.register(ProgramOffer)
class ProgramOfferAdmin(admin.ModelAdmin):
    list_display = ("name_fr", "program", "price_usd", "status", "position")
    list_filter = ("program", "status")
    search_fields = ("name_fr", "name_en", "program__title_fr")
    ordering = ("program", "position")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("program", "slug", "position")}),
        (_("Names"), {"fields": ("name_fr", "name_en")}),
        (_("Description"), {"fields": ("description_fr", "description_en")}),
        (_("Pricing"), {"fields": ("price_usd",)}),
        (_("Status"), {"fields": ("status", "created_at", "updated_at")}),
    )


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title_fr", "program", "resource_type", "status", "position")
    list_filter = ("program", "resource_type", "status")
    search_fields = ("title_fr", "title_en", "program__title_fr")
    ordering = ("program", "position")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("program", "resource_type", "position")}),
        (_("Titles"), {"fields": ("title_fr", "title_en")}),
        (_("Description"), {"fields": ("description_fr", "description_en")}),
        (_("File"), {"fields": ("file_path", "external_url")}),
        (_("Status"), {"fields": ("status", "created_at", "updated_at")}),
    )


class OrderAuditInline(admin.TabularInline):
    model = OrderAudit
    fields = ("created_at", "action", "old_status", "new_status", "user")
    readonly_fields = ("created_at", "action", "old_status", "new_status", "user")
    extra = 0
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user_email", "offer_name", "status", "price_usd", "created_at")
    list_filter = ("status", "organization", "created_at")
    search_fields = ("user__email", "offer__name_fr", "transaction_ref")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    inlines = [OrderAuditInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "organization",
                    "user",
                    "offer",
                )
            },
        ),
        (_("Purchase"), {"fields": ("price_usd", "created_at", "updated_at")}),
        (_("Payment"), {"fields": ("status", "transaction_ref")}),
        (_("Notes"), {"fields": ("notes",)}),
    )

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = _("User")

    def offer_name(self, obj):
        return obj.offer.name

    offer_name.short_description = _("Offer")

    actions = ["verify_payment", "cancel_order", "refund_order"]

    def verify_payment(self, request, queryset):
        """Mark orders as paid and create audit trail."""
        updated = 0
        for order in queryset.filter(status=Order.Status.PAYMENT_PENDING):
            order.status = Order.Status.PAID
            order.save()
            OrderAudit.objects.create(
                order=order,
                action=OrderAudit.Action.PAYMENT_VERIFIED,
                old_status=Order.Status.PAYMENT_PENDING,
                new_status=Order.Status.PAID,
                user=request.user,
            )
            updated += 1

        self.message_user(request, f"{updated} order(s) marked as paid")

    verify_payment.short_description = _("Verify payment (mark as Paid)")

    def cancel_order(self, request, queryset):
        """Cancel orders."""
        updated = 0
        for order in queryset.exclude(status__in=[Order.Status.CANCELLED, Order.Status.PAID, Order.Status.REFUNDED]):
            old_status = order.status
            order.status = Order.Status.CANCELLED
            order.save()
            OrderAudit.objects.create(
                order=order,
                action=OrderAudit.Action.CANCELLED,
                old_status=old_status,
                new_status=Order.Status.CANCELLED,
                user=request.user,
            )
            updated += 1

        self.message_user(request, f"{updated} order(s) cancelled")

    cancel_order.short_description = _("Cancel orders")

    def refund_order(self, request, queryset):
        """Refund paid orders."""
        updated = 0
        for order in queryset.filter(status=Order.Status.PAID):
            order.status = Order.Status.REFUNDED
            order.save()
            OrderAudit.objects.create(
                order=order,
                action=OrderAudit.Action.REFUNDED,
                old_status=Order.Status.PAID,
                new_status=Order.Status.REFUNDED,
                user=request.user,
            )
            updated += 1

        self.message_user(request, f"{updated} order(s) refunded")

    refund_order.short_description = _("Refund orders")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user_or_affiliate", "program", "offer_name", "status", "created_at")
    list_filter = ("program", "status", "organization")
    search_fields = ("user__email", "affiliate__name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("organization", "program", "user", "affiliate")}),
        (_("Access"), {"fields": ("offer", "order", "status", "access_until")}),
        (_("Progress"), {"fields": ("created_at",)}),
    )

    def user_or_affiliate(self, obj):
        if obj.user:
            return obj.user.email
        return obj.affiliate.name if obj.affiliate else "—"

    user_or_affiliate.short_description = _("Learner")

    def offer_name(self, obj):
        return obj.offer.name if obj.offer else "—"

    offer_name.short_description = _("Offer")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("enrollment_user", "lesson_title", "is_completed", "started_at")
    list_filter = ("completed_at",)
    search_fields = ("enrollment__user__email", "lesson__title_fr")
    readonly_fields = ("started_at", "completed_at")
    ordering = ("-started_at",)
    fieldsets = (
        (None, {"fields": ("enrollment", "lesson")}),
        (_("Progress"), {"fields": ("started_at", "completed_at")}),
    )

    def enrollment_user(self, obj):
        return obj.enrollment.user.email if obj.enrollment.user else obj.enrollment.affiliate.name

    enrollment_user.short_description = _("Learner")

    def lesson_title(self, obj):
        return obj.lesson.title

    lesson_title.short_description = _("Lesson")

    def is_completed(self, obj):
        return obj.is_completed()

    is_completed.boolean = True
    is_completed.short_description = _("Completed")
