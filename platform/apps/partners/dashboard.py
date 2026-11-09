"""Indicateurs du module partners pour le tableau de bord (données réelles)."""

from django.utils import timezone

from apps.core.models import OrganizationSettings
from apps.core.permissions import request_has_perm

from . import services
from .models import Affiliate


def partners_section(request):
    if not request_has_perm(request, "partners.view_affiliate"):
        return None
    settings_obj = OrganizationSettings.for_organization(request.organization)
    visible = services.visible_affiliates(request)
    current = visible.filter(archived_at__isnull=True)
    followups = services.open_followups(request)
    today = timezone.localdate()
    return {
        "order": 10,
        "template": "partners/dashboard_section.html",
        "context": {
            "total": current.count(),
            "active": current.filter(status=Affiliate.Status.ACTIVE).count(),
            "prospects": current.filter(status=Affiliate.Status.PROSPECT).count(),
            "registration_pending": services.registration_pending(visible).count(),
            "verification_pending": services.verification_pending(visible).count(),
            "followups_due": followups.filter(due_on__lte=today).count(),
            "followups_open": followups.count(),
            "alerts": {
                "contact_stale": services.contact_stale(visible, settings_obj).count(),
                "registration_stuck": services.registration_stuck(visible, settings_obj).count(),
                "verification_stuck": services.verification_stuck(visible, settings_obj).count(),
            },
            "thresholds": settings_obj,
            "can_view_followups": request_has_perm(request, "partners.view_followups"),
        },
    }
