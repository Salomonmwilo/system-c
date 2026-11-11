"""Règles de paiement garanties par PostgreSQL (phase C).

Commande :
- elle est créée non payée (brouillon, en attente de paiement ou paiement à vérifier) ;
- son statut ne suit que les transitions autorisées ; « payée » ne mène qu'à
  « remboursée », et « annulée » ou « remboursée » sont définitifs ;
- tout changement de statut exige la ligne d'historique correspondante (même
  ancien et nouveau statut) : aucune confirmation sans auteur ni note ;
- le montant remboursé ne fait qu'augmenter, seulement sur une commande payée,
  et vaut toujours la somme des remboursements de l'historique ;
- « remboursée » signifie remboursée intégralement.

Historique :
- une confirmation porte le prix et la devise de la commande ;
- un remboursement porte la devise de la commande.

Inscription :
- aucune inscription active ne peut viser une commande annulée ou remboursée.
"""

import re
from importlib import import_module

from django.db import migrations

ORDER_GUARD = r"""
CREATE OR REPLACE FUNCTION academy_order_guard() RETURNS trigger AS $$
DECLARE
    refunds numeric;
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.status <> 'draft' THEN
            RAISE EXCEPTION 'SYSTEMC: seule une commande en brouillon peut être supprimée'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        RETURN OLD;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM academy_programoffer o JOIN academy_program p ON p.id = o.program_id
        WHERE o.id = NEW.offer_id AND p.organization_id = NEW.organization_id
    ) THEN
        RAISE EXCEPTION 'SYSTEMC: la commande doit appartenir à l''organisation de son offre'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF TG_OP = 'INSERT' THEN
        IF NEW.status NOT IN ('draft', 'awaiting_payment', 'payment_pending') OR NEW.refunded_amount <> 0 THEN
            RAISE EXCEPTION 'SYSTEMC: une commande est créée non payée' USING ERRCODE = 'insufficient_privilege';
        END IF;
        RETURN NEW;
    END IF;

    IF (NEW.organization_id, NEW.user_id, NEW.offer_id, NEW.price, NEW.currency, NEW.created_at,
        NEW.risk_notice_version, NEW.terms_version)
        IS DISTINCT FROM (OLD.organization_id, OLD.user_id, OLD.offer_id, OLD.price, OLD.currency, OLD.created_at,
        OLD.risk_notice_version, OLD.terms_version) THEN
        RAISE EXCEPTION 'SYSTEMC: l''organisation, l''acheteur, l''offre, le prix, la devise et les textes acceptés d''une commande sont immuables'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    IF NEW.status IS DISTINCT FROM OLD.status THEN
        IF (OLD.status, NEW.status) NOT IN (
            ('draft', 'awaiting_payment'), ('draft', 'cancelled'),
            ('awaiting_payment', 'payment_pending'), ('awaiting_payment', 'paid'), ('awaiting_payment', 'cancelled'),
            ('payment_pending', 'paid'), ('payment_pending', 'cancelled'),
            ('paid', 'refunded')
        ) THEN
            RAISE EXCEPTION 'SYSTEMC: transition de commande interdite (% vers %)', OLD.status, NEW.status
                USING ERRCODE = 'insufficient_privilege';
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM academy_orderaudit a
            WHERE a.order_id = NEW.id AND a.old_status = OLD.status AND a.new_status = NEW.status
        ) THEN
            RAISE EXCEPTION 'SYSTEMC: changement de statut sans ligne d''historique' USING ERRCODE = 'insufficient_privilege';
        END IF;
    END IF;

    IF NEW.refunded_amount <> OLD.refunded_amount THEN
        IF NEW.refunded_amount < OLD.refunded_amount OR OLD.status <> 'paid' THEN
            RAISE EXCEPTION 'SYSTEMC: remboursement impossible sur cette commande' USING ERRCODE = 'insufficient_privilege';
        END IF;
        SELECT COALESCE(SUM(amount), 0) INTO refunds FROM academy_orderaudit
        WHERE order_id = NEW.id AND action IN ('refunded', 'partial_refund');
        IF refunds <> NEW.refunded_amount THEN
            RAISE EXCEPTION 'SYSTEMC: le montant remboursé ne correspond pas à l''historique' USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    END IF;

    IF NEW.status = 'refunded' AND NEW.refunded_amount <> NEW.price THEN
        RAISE EXCEPTION 'SYSTEMC: « remboursée » signifie remboursée intégralement' USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

AUDIT_GUARD = r"""
CREATE OR REPLACE FUNCTION academy_orderaudit_guard() RETURNS trigger AS $$
DECLARE
    o academy_order%ROWTYPE;
BEGIN
    SELECT * INTO o FROM academy_order WHERE id = NEW.order_id;
    IF NEW.action = 'payment_verified' AND (NEW.amount IS DISTINCT FROM o.price OR NEW.currency IS DISTINCT FROM o.currency) THEN
        RAISE EXCEPTION 'SYSTEMC: une confirmation porte le prix et la devise de la commande'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF NEW.action IN ('refunded', 'partial_refund') AND NEW.currency IS DISTINCT FROM o.currency THEN
        RAISE EXCEPTION 'SYSTEMC: un remboursement est dans la devise de la commande'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER academy_orderaudit_guard BEFORE INSERT ON academy_orderaudit
FOR EACH ROW EXECUTE FUNCTION academy_orderaudit_guard();
"""

ENROLLMENT_GUARD = r"""
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
    IF NEW.status = 'active' AND NEW.order_id IS NOT NULL AND EXISTS (
        SELECT 1 FROM academy_order c WHERE c.id = NEW.order_id AND c.status IN ('cancelled', 'refunded')
    ) THEN
        RAISE EXCEPTION 'SYSTEMC: une inscription ne peut pas être réactivée sur une commande annulée ou remboursée'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def _previous(function_name: str) -> str:
    """Corps de la fonction tel qu'installé par 0006, pour le retour arrière."""
    sql = import_module("apps.academy.migrations.0006_integrity_triggers").SQL
    match = re.search(
        rf"CREATE OR REPLACE FUNCTION {function_name}\(\).*?\$\$ LANGUAGE plpgsql;", sql, re.S
    )
    return match.group(0)


class Migration(migrations.Migration):
    dependencies = [("academy", "0007_payments_and_uniqueness")]

    operations = [
        migrations.RunSQL(ORDER_GUARD, reverse_sql=_previous("academy_order_guard")),
        migrations.RunSQL(
            AUDIT_GUARD,
            reverse_sql="DROP TRIGGER IF EXISTS academy_orderaudit_guard ON academy_orderaudit; "
            "DROP FUNCTION IF EXISTS academy_orderaudit_guard();",
        ),
        migrations.RunSQL(ENROLLMENT_GUARD, reverse_sql=_previous("academy_enrollment_guard")),
    ]
