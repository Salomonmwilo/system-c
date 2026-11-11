"""Règles en base pour la confirmation de sa propre commande, les données de
démonstration et la révocation d'accès.

- Personne ne confirme le paiement de sa propre commande, sauf sur un programme
  de démonstration (l'application exige en plus que DEBUG soit actif).
- L'indicateur « démonstration » d'un programme ne change plus après création :
  un vrai programme ne peut pas devenir « démo » pour contourner la règle.
- Une révocation d'accès ne vise qu'une commande payée ayant un remboursement
  partiel ; une inscription révoquée ne redevient pas active.
"""

import re
from importlib import import_module

from django.db import migrations

PARENT_GUARD = r"""
CREATE OR REPLACE FUNCTION academy_parent_guard() RETURNS trigger AS $$
BEGIN
    -- IF imbriqués : NEW.program_id n'existe pas sur academy_program, ni NEW.organization_id ailleurs.
    IF TG_TABLE_NAME = 'academy_program' THEN
        IF NEW.organization_id <> OLD.organization_id THEN
            RAISE EXCEPTION 'SYSTEMC: un programme ne change pas d''organisation' USING ERRCODE = 'integrity_constraint_violation';
        END IF;
        IF NEW.is_demo <> OLD.is_demo THEN
            RAISE EXCEPTION 'SYSTEMC: l''indicateur de démonstration d''un programme est fixé à sa création'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
    ELSE
        IF NEW.program_id <> OLD.program_id THEN
            RAISE EXCEPTION 'SYSTEMC: % ne change pas de programme', TG_TABLE_NAME USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

AUDIT_GUARD = r"""
CREATE OR REPLACE FUNCTION academy_orderaudit_guard() RETURNS trigger AS $$
DECLARE
    o academy_order%ROWTYPE;
    demo boolean;
BEGIN
    SELECT * INTO o FROM academy_order WHERE id = NEW.order_id;
    IF NEW.action = 'payment_verified' AND (NEW.amount IS DISTINCT FROM o.price OR NEW.currency IS DISTINCT FROM o.currency) THEN
        RAISE EXCEPTION 'SYSTEMC: une confirmation porte le prix et la devise de la commande'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF NEW.action = 'payment_verified' AND NEW.actor_id = o.user_id THEN
        SELECT p.is_demo INTO demo FROM academy_programoffer f JOIN academy_program p ON p.id = f.program_id
        WHERE f.id = o.offer_id;
        IF NOT demo THEN
            RAISE EXCEPTION 'SYSTEMC: personne ne confirme le paiement de sa propre commande'
                USING ERRCODE = 'insufficient_privilege';
        END IF;
    END IF;
    IF NEW.action IN ('refunded', 'partial_refund') AND NEW.currency IS DISTINCT FROM o.currency THEN
        RAISE EXCEPTION 'SYSTEMC: un remboursement est dans la devise de la commande'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF NEW.action = 'access_revoked' AND NOT (o.status = 'paid' AND o.refunded_amount > 0) THEN
        RAISE EXCEPTION 'SYSTEMC: une révocation d''accès suit un remboursement partiel d''une commande payée'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
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
    IF NEW.status = 'active' AND (
        (TG_OP = 'UPDATE' AND OLD.status = 'revoked')
        OR (NEW.order_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM academy_orderaudit a WHERE a.order_id = NEW.order_id AND a.action = 'access_revoked'
        ))
    ) THEN
        RAISE EXCEPTION 'SYSTEMC: un accès révoqué ne redevient pas actif' USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def _previous(module: str, function_name: str) -> str:
    sql = "".join(
        value for name, value in vars(import_module(f"apps.academy.migrations.{module}")).items()
        if isinstance(value, str) and name.isupper()
    )
    return re.search(rf"CREATE OR REPLACE FUNCTION {function_name}\(\).*?\$\$ LANGUAGE plpgsql;", sql, re.S).group(0)


class Migration(migrations.Migration):
    dependencies = [("academy", "0010_demo_access_revocation")]

    operations = [
        migrations.RunSQL(PARENT_GUARD, reverse_sql=_previous("0006_integrity_triggers", "academy_parent_guard")),
        migrations.RunSQL(AUDIT_GUARD, reverse_sql=_previous("0008_payment_triggers", "academy_orderaudit_guard")),
        migrations.RunSQL(ENROLLMENT_GUARD, reverse_sql=_previous("0008_payment_triggers", "academy_enrollment_guard")),
    ]
