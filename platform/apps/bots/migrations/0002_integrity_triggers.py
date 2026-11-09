"""Protections en base de données du CRM bots.

- Une version validée (et ses paramètres) ne peut être ni modifiée ni supprimée.
- Les déclarations d'application et l'historique de statut sont en ajout seul.
- Une déclaration ne peut viser qu'une version validée.
- Une fiche robot, ses versions et ses déclarations restent dans l'organisation
  de l'affilié (isolation stricte, même en cas d'erreur applicative).
"""

from django.db import migrations

SQL = r"""
CREATE OR REPLACE FUNCTION bots_version_guard() RETURNS trigger AS $$
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') AND OLD.state = 'validated' THEN
        RAISE EXCEPTION 'SYSTEMC: une version validée est immuable (% interdit)', TG_OP
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        IF NOT EXISTS (
            SELECT 1 FROM bots_botuser b WHERE b.id = NEW.bot_user_id AND b.organization_id = NEW.organization_id
        ) THEN
            RAISE EXCEPTION 'SYSTEMC: organisation incohérente pour la version' USING ERRCODE = 'integrity_constraint_violation';
        END IF;
        RETURN NEW;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bots_version_guard
BEFORE INSERT OR UPDATE OR DELETE ON bots_configurationversion
FOR EACH ROW EXECUTE FUNCTION bots_version_guard();

CREATE OR REPLACE FUNCTION bots_parameter_guard() RETURNS trigger AS $$
DECLARE
    parent_state text;
BEGIN
    IF TG_OP = 'DELETE' THEN
        SELECT state INTO parent_state FROM bots_configurationversion WHERE id = OLD.version_id;
    ELSE
        SELECT state INTO parent_state FROM bots_configurationversion WHERE id = NEW.version_id;
        IF TG_OP = 'UPDATE' AND OLD.version_id <> NEW.version_id THEN
            RAISE EXCEPTION 'SYSTEMC: un paramètre ne change pas de version' USING ERRCODE = 'insufficient_privilege';
        END IF;
    END IF;
    IF parent_state = 'validated' THEN
        RAISE EXCEPTION 'SYSTEMC: les paramètres d''une version validée sont immuables'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bots_parameter_guard
BEFORE INSERT OR UPDATE OR DELETE ON bots_parametervalue
FOR EACH ROW EXECUTE FUNCTION bots_parameter_guard();

CREATE OR REPLACE FUNCTION bots_declaration_guard() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM bots_configurationversion v
        WHERE v.id = NEW.version_id AND v.state = 'validated' AND v.organization_id = NEW.organization_id
    ) THEN
        RAISE EXCEPTION 'SYSTEMC: une déclaration doit viser une version validée de la même organisation'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bots_declaration_insert_guard
BEFORE INSERT ON bots_applicationdeclaration
FOR EACH ROW EXECUTE FUNCTION bots_declaration_guard();

CREATE TRIGGER bots_applicationdeclaration_append_only
BEFORE UPDATE OR DELETE ON bots_applicationdeclaration
FOR EACH ROW EXECUTE FUNCTION systemc_forbid_change();

CREATE TRIGGER bots_statusevent_append_only
BEFORE UPDATE OR DELETE ON bots_statusevent
FOR EACH ROW EXECUTE FUNCTION systemc_forbid_change();

CREATE OR REPLACE FUNCTION bots_botuser_org_guard() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM partners_affiliate a WHERE a.id = NEW.affiliate_id AND a.organization_id = NEW.organization_id
    ) THEN
        RAISE EXCEPTION 'SYSTEMC: la fiche robot doit appartenir à l''organisation de l''affilié'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bots_botuser_org_guard
BEFORE INSERT OR UPDATE OF organization_id, affiliate_id ON bots_botuser
FOR EACH ROW EXECUTE FUNCTION bots_botuser_org_guard();
"""

REVERSE_SQL = r"""
DROP TRIGGER IF EXISTS bots_botuser_org_guard ON bots_botuser;
DROP FUNCTION IF EXISTS bots_botuser_org_guard();
DROP TRIGGER IF EXISTS bots_statusevent_append_only ON bots_statusevent;
DROP TRIGGER IF EXISTS bots_applicationdeclaration_append_only ON bots_applicationdeclaration;
DROP TRIGGER IF EXISTS bots_declaration_insert_guard ON bots_applicationdeclaration;
DROP FUNCTION IF EXISTS bots_declaration_guard();
DROP TRIGGER IF EXISTS bots_parameter_guard ON bots_parametervalue;
DROP FUNCTION IF EXISTS bots_parameter_guard();
DROP TRIGGER IF EXISTS bots_version_guard ON bots_configurationversion;
DROP FUNCTION IF EXISTS bots_version_guard();
"""


class Migration(migrations.Migration):
    dependencies = [("bots", "0001_initial"), ("core", "0002_append_only_triggers"), ("partners", "0002_append_only_triggers")]

    operations = [migrations.RunSQL(SQL, reverse_sql=REVERSE_SQL)]
