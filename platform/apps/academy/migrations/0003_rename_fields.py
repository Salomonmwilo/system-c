"""Renommages sans perte de données.

- ``price_usd`` devient ``price`` accompagné d'une devise (USD pour les lignes existantes) ;
- ``Resource.resource_type`` devient ``category`` et ``file_path`` devient ``file`` ;
- ``OrderAudit.user`` devient ``actor``.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("academy", "0002_extend_academy_for_commerce")]

    operations = [
        migrations.RenameField("programoffer", "price_usd", "price"),
        migrations.AddField(
            "programoffer", "currency", models.CharField(default="USD", max_length=3, verbose_name="currency")
        ),
        migrations.RenameField("order", "price_usd", "price"),
        migrations.AddField(
            "order",
            "currency",
            models.CharField(default="USD", max_length=3, verbose_name="currency"),
            preserve_default=False,
        ),
        migrations.RenameField("resource", "resource_type", "category"),
        migrations.RenameField("resource", "file_path", "file"),
        migrations.RenameField("orderaudit", "user", "actor"),
    ]
