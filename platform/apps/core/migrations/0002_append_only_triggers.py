"""Fonction PostgreSQL réutilisable qui interdit UPDATE et DELETE.

Elle protège les tables en ajout seul (journal d'audit, historiques), y compris
contre une requête SQL directe qui contournerait l'ORM.
"""

from django.db import migrations

CREATE_FUNCTION = """
CREATE OR REPLACE FUNCTION systemc_forbid_change() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'SYSTEMC: % est en ajout seul (% interdit)', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;
"""

AUDIT_TRIGGER = """
CREATE TRIGGER core_auditlog_append_only
BEFORE UPDATE OR DELETE ON core_auditlog
FOR EACH ROW EXECUTE FUNCTION systemc_forbid_change();
"""


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.RunSQL(CREATE_FUNCTION, reverse_sql="DROP FUNCTION IF EXISTS systemc_forbid_change() CASCADE;"),
        migrations.RunSQL(AUDIT_TRIGGER, reverse_sql="DROP TRIGGER IF EXISTS core_auditlog_append_only ON core_auditlog;"),
    ]
