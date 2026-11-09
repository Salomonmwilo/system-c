from django.db import migrations

TABLES = ["partners_trackevent", "partners_interaction"]


def forward_sql():
    return "\n".join(
        f"CREATE TRIGGER {t}_append_only BEFORE UPDATE OR DELETE ON {t} "
        f"FOR EACH ROW EXECUTE FUNCTION systemc_forbid_change();"
        for t in TABLES
    )


def reverse_sql():
    return "\n".join(f"DROP TRIGGER IF EXISTS {t}_append_only ON {t};" for t in TABLES)


class Migration(migrations.Migration):
    dependencies = [("partners", "0001_initial"), ("core", "0002_append_only_triggers")]

    operations = [migrations.RunSQL(forward_sql(), reverse_sql=reverse_sql())]
