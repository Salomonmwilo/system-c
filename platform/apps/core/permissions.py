"""Politique d'autorisation centralisée, appliquée côté serveur.

Règle : refus par défaut. Une permission absente de ``PERMISSIONS`` est refusée.
Les permissions sont toujours évaluées pour l'organisation courante : un rôle
détenu dans une autre organisation ne donne aucun droit ici. Le statut de
super-utilisateur Django ne donne aucun accès aux données d'une organisation.
"""

from __future__ import annotations

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect

from .models import Role

R = Role

# Rôles qui voient tous les affiliés de l'organisation (les conseillers ne voient
# que les affiliés qui leur sont attribués).
FULL_AFFILIATE_VISIBILITY = frozenset(
    {R.ORG_ADMIN, R.CRM_ADMIN, R.CRM_OPERATOR, R.CRM_VIEWER, R.PARTNER_MANAGER}
)

PERMISSIONS: dict[str, frozenset[str]] = {
    # core
    "core.view_dashboard": frozenset(
        {R.ORG_ADMIN, R.CRM_ADMIN, R.CRM_OPERATOR, R.CRM_VIEWER, R.PARTNER_MANAGER, R.PARTNER_ADVISOR}
    ),
    "core.manage_members": frozenset({R.ORG_ADMIN}),
    "core.view_audit": frozenset({R.ORG_ADMIN, R.CRM_ADMIN}),
    "core.manage_thresholds": frozenset({R.CRM_ADMIN}),
    # partners
    "partners.view_affiliate": frozenset(
        {R.ORG_ADMIN, R.CRM_ADMIN, R.CRM_OPERATOR, R.CRM_VIEWER, R.PARTNER_MANAGER, R.PARTNER_ADVISOR}
    ),
    "partners.view_pii": frozenset(
        {R.ORG_ADMIN, R.CRM_ADMIN, R.CRM_OPERATOR, R.PARTNER_MANAGER, R.PARTNER_ADVISOR}
    ),
    "partners.add_affiliate": frozenset({R.CRM_ADMIN, R.PARTNER_MANAGER}),
    "partners.change_affiliate": frozenset({R.CRM_ADMIN, R.PARTNER_MANAGER, R.PARTNER_ADVISOR}),
    "partners.archive_affiliate": frozenset({R.CRM_ADMIN, R.PARTNER_MANAGER}),
    "partners.update_tracks": frozenset({R.CRM_ADMIN, R.CRM_OPERATOR, R.PARTNER_MANAGER, R.PARTNER_ADVISOR}),
    "partners.add_interaction": frozenset({R.CRM_ADMIN, R.CRM_OPERATOR, R.PARTNER_MANAGER, R.PARTNER_ADVISOR}),
    "partners.view_followups": frozenset(
        {R.ORG_ADMIN, R.CRM_ADMIN, R.CRM_OPERATOR, R.CRM_VIEWER, R.PARTNER_MANAGER, R.PARTNER_ADVISOR}
    ),
    "partners.manage_followups": frozenset({R.CRM_ADMIN, R.CRM_OPERATOR, R.PARTNER_MANAGER, R.PARTNER_ADVISOR}),
    "partners.manage_referral_links": frozenset({R.CRM_ADMIN, R.PARTNER_MANAGER}),
    # bots (CRM administratif, aucun contrôle des robots)
    "bots.view_botuser": frozenset({R.ORG_ADMIN, R.CRM_ADMIN, R.CRM_OPERATOR, R.CRM_VIEWER}),
    "bots.add_botuser": frozenset({R.CRM_ADMIN, R.CRM_OPERATOR}),
    "bots.change_botuser": frozenset({R.CRM_ADMIN, R.CRM_OPERATOR}),
    "bots.prepare_version": frozenset({R.CRM_ADMIN, R.CRM_OPERATOR}),
    "bots.validate_version": frozenset({R.CRM_ADMIN}),
    "bots.declare_applied": frozenset({R.CRM_ADMIN, R.CRM_OPERATOR}),
    "bots.correct_declaration": frozenset({R.CRM_ADMIN, R.CRM_OPERATOR}),
    # Tout ce qui concerne un compte réel : réservé à crm_admin.
    "bots.manage_real": frozenset({R.CRM_ADMIN}),
    "bots.pause": frozenset({R.CRM_ADMIN, R.CRM_OPERATOR}),
    "bots.disable": frozenset({R.CRM_ADMIN}),
    "bots.manage_parameters": frozenset({R.CRM_ADMIN}),
    # academy
    "academy.view": frozenset({R.ORG_ADMIN, R.CRM_ADMIN, R.ACADEMY_INSTRUCTOR, R.ACADEMY_STUDENT}),
    "academy.buy": frozenset({R.ORG_ADMIN, R.CRM_ADMIN, R.ACADEMY_INSTRUCTOR, R.ACADEMY_STUDENT}),
    # payments : commandes d'Academy. Réservé à org_admin pour la première version ;
    # un futur rôle finance_admin pourra s'ajouter ici. Le statut de super-utilisateur
    # ne donne aucune de ces permissions.
    "payments.view_orders": frozenset({R.ORG_ADMIN}),
    "payments.confirm_order": frozenset({R.ORG_ADMIN}),
    "payments.cancel_order": frozenset({R.ORG_ADMIN}),
    "payments.refund_order": frozenset({R.ORG_ADMIN}),
    "payments.revoke_access": frozenset({R.ORG_ADMIN}),
}


def roles_have_perm(roles, perm: str) -> bool:
    allowed = PERMISSIONS.get(perm)
    if allowed is None:
        return False
    return bool(allowed.intersection(roles))


def request_has_perm(request, perm: str) -> bool:
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or getattr(request, "organization", None) is None:
        return False
    return roles_have_perm(getattr(request, "org_roles", frozenset()), perm)


def require_perm(request, perm: str) -> None:
    if not request_has_perm(request, perm):
        raise PermissionDenied


def has_full_affiliate_visibility(request) -> bool:
    return bool(FULL_AFFILIATE_VISIBILITY.intersection(getattr(request, "org_roles", frozenset())))


class OrgPermissionRequiredMixin(AccessMixin):
    """Exige une connexion, une organisation courante et toutes les permissions listées."""

    permission_required: str | tuple[str, ...] = ()

    def get_permissions(self) -> tuple[str, ...]:
        perms = self.permission_required
        if isinstance(perms, str):
            perms = (perms,)
        if not perms:
            raise PermissionDenied  # refus par défaut si la vue n'a rien déclaré
        return tuple(perms)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.organization is None:
            return redirect("core:no_organization")
        for perm in self.get_permissions():
            if not request_has_perm(request, perm):
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def has_perm(self, perm: str) -> bool:
        return request_has_perm(self.request, perm)


def get_for_org(request, model_or_queryset, **lookup):
    """Récupère un objet de l'organisation courante ; 404 sinon (jamais 403)."""
    queryset = getattr(model_or_queryset, "objects", model_or_queryset)
    if hasattr(queryset, "all"):
        queryset = queryset.all()
    return get_object_or_404(queryset.filter(organization=request.organization), **lookup)
