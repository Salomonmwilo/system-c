# Generated manually for SYSTEM-C Method commercial features.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academy", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProgramOffer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=100)),
                ("name_fr", models.CharField(max_length=200, verbose_name="name (French)")),
                ("name_en", models.CharField(max_length=200, verbose_name="name (English)")),
                ("description_fr", models.TextField(blank=True, verbose_name="description (French)")),
                ("description_en", models.TextField(blank=True, verbose_name="description (English)")),
                ("price_usd", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="price (USD)")),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")],
                        default="draft",
                        max_length=16,
                    ),
                ),
                ("position", models.PositiveSmallIntegerField(default=1)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "program",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offers", to="academy.program"),
                ),
            ],
            options={
                "ordering": ["position"],
            },
        ),
        migrations.CreateModel(
            name="Resource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title_fr", models.CharField(max_length=200, verbose_name="title (French)")),
                ("title_en", models.CharField(max_length=200, verbose_name="title (English)")),
                ("description_fr", models.TextField(blank=True, verbose_name="description (French)")),
                ("description_en", models.TextField(blank=True, verbose_name="description (English)")),
                (
                    "resource_type",
                    models.CharField(
                        choices=[
                            ("guide", "Guide"),
                            ("video", "Video"),
                            ("worksheet", "Worksheet"),
                            ("checklist", "Checklist"),
                            ("exercise", "Exercise"),
                            ("other", "Other"),
                        ],
                        default="guide",
                        max_length=20,
                    ),
                ),
                ("file_path", models.FileField(blank=True, upload_to="academy/resources/%Y/%m/", verbose_name="file")),
                ("external_url", models.URLField(blank=True, verbose_name="external URL")),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")],
                        default="draft",
                        max_length=16,
                    ),
                ),
                ("position", models.PositiveSmallIntegerField(default=1)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "program",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="resources", to="academy.program"),
                ),
            ],
            options={
                "ordering": ["position"],
            },
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("price_usd", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="price at purchase (USD)")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("awaiting_payment", "Awaiting payment"),
                            ("payment_pending", "Payment pending verification"),
                            ("paid", "Paid and confirmed"),
                            ("cancelled", "Cancelled"),
                            ("refunded", "Refunded"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("transaction_ref", models.CharField(blank=True, max_length=100, verbose_name="transaction reference")),
                ("notes", models.TextField(blank=True, verbose_name="admin notes")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "offer",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="academy.programoffer"),
                ),
                (
                    "organization",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academy_orders", to="core.organization"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="academy_orders", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="OrderAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("status_changed", "Status changed"),
                            ("payment_verified", "Payment verified"),
                            ("refunded", "Refunded"),
                            ("cancelled", "Cancelled"),
                        ],
                        max_length=30,
                    ),
                ),
                ("old_status", models.CharField(blank=True, max_length=20)),
                ("new_status", models.CharField(blank=True, max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "order",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_log", to="academy.order"),
                ),
                (
                    "user",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="enrollment",
            name="offer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="enrollments",
                to="academy.programoffer",
            ),
        ),
        migrations.AddField(
            model_name="enrollment",
            name="order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="enrollments",
                to="academy.order",
            ),
        ),
        migrations.AddField(
            model_name="enrollment",
            name="access_until",
            field=models.DateTimeField(blank=True, null=True, verbose_name="access expires"),
        ),
        migrations.AlterField(
            model_name="enrollment",
            name="status",
            field=models.CharField(
                choices=[
                    ("requested", "Requested"),
                    ("active", "Active"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                    ("suspended", "Suspended"),
                ],
                default="requested",
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="LessonProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "enrollment",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lesson_progress", to="academy.enrollment"),
                ),
                (
                    "lesson",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="progress_records", to="academy.lesson"),
                ),
            ],
            options={
                "unique_together": {("enrollment", "lesson")},
            },
        ),
        migrations.AddConstraint(
            model_name="programoffer",
            constraint=models.UniqueConstraint(fields=["program", "slug"], name="unique_program_offer_slug"),
        ),
    ]
