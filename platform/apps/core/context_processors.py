from django.conf import settings

from .permissions import request_has_perm

NAV_PERMISSIONS = {
    "dashboard": "core.view_dashboard",
    "affiliates": "partners.view_affiliate",
    "followups": "partners.view_followups",
    "referral_links": "partners.manage_referral_links",
    "bots": "bots.view_botuser",
    "parameters": "bots.manage_parameters",
    "academy": "academy.view",
    "academy_orders": "payments.view_orders",
    "members": "core.manage_members",
    "thresholds": "core.manage_thresholds",
    "audit": "core.view_audit",
}


def platform(request):
    nav = {key: request_has_perm(request, perm) for key, perm in NAV_PERMISSIONS.items()}
    return {
        "nav": nav,
        "current_organization": getattr(request, "organization", None),
        "user_organizations": getattr(request, "user_organizations", []),
        "available_languages": settings.LANGUAGES,
    }
