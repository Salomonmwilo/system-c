"""Protections en base de données du module academy.

Elles tiennent même si une vue ou un script oublie une vérification :
- un programme ne change pas d'organisation ; une étape, une offre ou une
  ressource ne change pas de programme ; une leçon reste dans son programme ;
- une commande appartient à l'organisation de son offre ; son organisation,
  son acheteur, son offre, son prix et sa devise ne changent plus après
  création ; seule une commande en brouillon peut être supprimée ;
- l'historique des commandes est en ajout seul ;
- une inscription reste cohérente avec son programme, son offre, sa commande
  (même acheteur, même offre) et l'affilié éventuel (même organisation) ;
- une ressource n'est incluse que dans les offres de son propre programme ;
- une progression ne vise qu'une leçon du programme de l'inscription.
"""

from django.db import migrations

SQL = r"""
CREATE OR REPLACE FUNCTION academy_parent_guard() RETURNS trigger AS $$
BEGIN
    -- IF imbriqués : NEW.program_id n'existe pas sur academy_program, ni NEW.organization_id ailleurs.
    IF TG_TABLE_NAME = 'academy_program' THEN
        IF NEW.organization_id <> OLD.organization_id THEN
            RAISE EXCEPTION 'SYSTEMC: un programme ne change pas d''organisation' USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    ELSE
        IF NEW.program_id <> OLD.program_id THEN
            RAISE EXCEPTION 'SYSTEMC: % ne change pas de programme', TG_TABLE_NAME USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER academy_program_parent_guard BEFORE UPDATE ON academy_program
FOR EACH ROW EXECUTE FUNCTION academy_parent_guard();
CREATE TRIGGER academy_course_parent_guard BEFORE UPDATE ON academy_course
FOR EACH ROW EXECUTE FUNCTION academy_parent_guard();
CREATE TRIGGER academy_programoffer_parent_guard BEFORE UPDATE ON academy_programoffer
FOR EACH ROW EXECUTE FUNCTION academy_parent_guard();
CREATE TRIGGER academy_resource_parent_guard BEFORE UPDATE ON academy_resource
FOR EACH ROW EXECUTE FUNCTION academy_parent_guard();

CREATE OR REPLACE FUNCTION academy_lesson_guard() RETURNS trigger AS $$
BEGIN
    IF NEW.course_id <> OLD.course_id AND NOT EXISTS (
        SELECT 1 FROM academy_course a JOIN academy_course b ON a.program_id = b.program_id
        WHERE a.id = OLD.course_id AND b.id = NEW.course_id
    ) THEN
        RAISE EXCEPTION 'SYSTEMC: une leçon reste dans son programme' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER academy_lesson_guard BEFORE UPDATE ON academy_lesson
FOR EACH ROW EXECUTE FUNCTION academy_lesson_guard();

CREATE OR REPLACE FUNCTION academy_order_guard() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.status <> 'draft' THEN
            RAISE EXCEPTION 'SYSTEMC: seule une commande en brouillon peut être supprimée'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        RETURN OLD;
    END IF;
    IF TG_OP = 'UPDATE' AND (NEW.organization_id, NEW.user_id, NEW.offer_id, NEW.price, NEW.currency, NEW.created_at)
        IS DISTINCT FROM (OLD.organization_id, OLD.user_id, OLD.offer_id, OLD.price, OLD.currency, OLD.created_at) THEN
        RAISE EXCEPTION 'SYSTEMC: l''organisation, l''acheteur, l''offre, le prix et la devise d''une commande sont immuables'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM academy_programoffer o JOIN academy_program p ON p.id = o.program_id
        WHERE o.id = NEW.offer_id AND p.organization_id = NEW.organization_id
    ) THEN
        RAISE EXCEPTION 'SYSTEMC: la commande doit appartenir à l''organisation de son offre'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER academy_order_guard BEFORE INSERT OR UPDATE OR DELETE ON academy_order
FOR EACH ROW EXECUTE FUNCTION academy_order_guard();

CREATE TRIGGER academy_orderaudit_append_only BEFORE UPDATE OR DELETE ON academy_orderaudit
FOR EACH ROW EXECUTE FUNCTION systemc_forbid_change();

CREATE OR REPLACE FUNCTION academy_enrollment_guard() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM academy_program p WHERE p.id = NEW.program_id AND p.organization_id = NEW.organization_id
    ) THEN
        RAISE EXCEPTION 'SYSTEMC: l''inscription doit appartenir à l''organisation du programme'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF NEW.offer_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM academy_programoffer o WHERE o.id = NEW.offer_id AND o.program_id = NEW.program_id
    ) THEN
        RAISE EXCEPTION 'SYSTEMC: l''offre de l''inscription appartient à un autre programme'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF NEW.order_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM academy_order c
        WHERE c.id = NEW.order_id AND c.organization_id = NEW.organization_id
          AND c.user_id IS NOT DISTINCT FROM NEW.user_id AND c.offer_id IS NOT DISTINCT FROM NEW.offer_id
    ) THEN
        RAISE EXCEPTION 'SYSTEMC: l''inscription doit reprendre l''acheteur et l''offre de sa commande'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF NEW.affiliate_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM partners_affiliate a WHERE a.id = NEW.affiliate_id AND a.organization_id = NEW.organization_id
    ) THEN
        RAISE EXCEPTION 'SYSTEMC: l''affilié appartient à une autre organisation'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER academy_enrollment_guard BEFORE INSERT OR UPDATE ON academy_enrollment
FOR EACH ROW EXECUTE FUNCTION academy_enrollment_guard();

CREATE OR REPLACE FUNCTION academy_resource_offer_guard() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM academy_resource r JOIN academy_programoffer o ON o.program_id = r.program_id
        WHERE r.id = NEW.resource_id AND o.id = NEW.programoffer_id
    ) THEN
        RAISE EXCEPTION 'SYSTEMC: une ressource n''est incluse que dans les offres de son programme'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER academy_resource_offer_guard BEFORE INSERT OR UPDATE ON academy_resource_offers
FOR EACH ROW EXECUTE FUNCTION academy_resource_offer_guard();

CREATE OR REPLACE FUNCTION academy_progress_guard() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM academy_lesson l
        JOIN academy_course c ON c.id = l.course_id
        JOIN academy_enrollment e ON e.program_id = c.program_id
        WHERE l.id = NEW.lesson_id AND e.id = NEW.enrollment_id
    ) THEN
        RAISE EXCEPTION 'SYSTEMC: la leçon n''appartient pas au programme de l''inscription'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER academy_progress_guard BEFORE INSERT OR UPDATE ON academy_lessonprogress
FOR EACH ROW EXECUTE FUNCTION academy_progress_guard();
"""

REVERSE_SQL = r"""
DROP TRIGGER IF EXISTS academy_progress_guard ON academy_lessonprogress;
DROP FUNCTION IF EXISTS academy_progress_guard();
DROP TRIGGER IF EXISTS academy_resource_offer_guard ON academy_resource_offers;
DROP FUNCTION IF EXISTS academy_resource_offer_guard();
DROP TRIGGER IF EXISTS academy_enrollment_guard ON academy_enrollment;
DROP FUNCTION IF EXISTS academy_enrollment_guard();
DROP TRIGGER IF EXISTS academy_orderaudit_append_only ON academy_orderaudit;
DROP TRIGGER IF EXISTS academy_order_guard ON academy_order;
DROP FUNCTION IF EXISTS academy_order_guard();
DROP TRIGGER IF EXISTS academy_lesson_guard ON academy_lesson;
DROP FUNCTION IF EXISTS academy_lesson_guard();
DROP TRIGGER IF EXISTS academy_resource_parent_guard ON academy_resource;
DROP TRIGGER IF EXISTS academy_programoffer_parent_guard ON academy_programoffer;
DROP TRIGGER IF EXISTS academy_course_parent_guard ON academy_course;
DROP TRIGGER IF EXISTS academy_program_parent_guard ON academy_program;
DROP FUNCTION IF EXISTS academy_parent_guard();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("academy", "0005_reshape_seeded_content"),
        ("core", "0002_append_only_triggers"),
        ("partners", "0002_append_only_triggers"),
    ]

    operations = [migrations.RunSQL(SQL, reverse_sql=REVERSE_SQL)]
