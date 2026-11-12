from django.conf import settings

from .models import Role
from .permissions import request_has_perm
from .registry import notifications

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


def _main_role(request) -> str:
    roles = getattr(request, "org_roles", frozenset())
    return next((label for value, label in Role.choices if value in roles), "")


def _initials(user) -> str:
    if user is None or not user.is_authenticated:
        return ""
    parts = (user.full_name or user.email).split()
    return "".join(part[0] for part in parts[:2]).upper()


def platform(request):
    nav = {key: request_has_perm(request, perm) for key, perm in NAV_PERMISSIONS.items()}
    alerts = notifications(request) if getattr(request, "organization", None) else []
    return {
        "notifications": alerts,
        "notifications_total": sum(item["count"] for item in alerts),
        "main_role": _main_role(request),
        "user_initials": _initials(getattr(request, "user", None)),
        "can_search": request_has_perm(request, "core.search"),
        "nav": nav,
        "current_organization": getattr(request, "organization", None),
        "user_organizations": getattr(request, "user_organizations", []),
        "available_languages": settings.LANGUAGES,
    }
