"""Indicateurs du module partners pour le tableau de bord (données réelles).

Chaque fournisseur renvoie un résumé et des « priorités » : des lignes du registre
« À traiter », triées par le tableau de bord selon leur rang d'urgence.
"""

from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

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
    followups_due = followups.filter(due_on__lte=today).count()
    followups_overdue = followups.filter(due_on__lt=today).count()
    alerts = {
        "contact_stale": services.contact_stale(visible, settings_obj).count(),
        "registration_stuck": services.registration_stuck(visible, settings_obj).count(),
        "verification_stuck": services.verification_stuck(visible, settings_obj).count(),
    }
    affiliates_url = reverse("partners:affiliate_list")
    priorities = []
    if request_has_perm(request, "partners.view_followups"):
        priorities.append({
            "rank": 10,
            "count": followups_due,
            "label": ngettext("Follow-up to do today", "Follow-ups to do today", followups_due),
            "hint": ngettext("%(n)s overdue", "%(n)s overdue", followups_overdue) % {"n": followups_overdue}
            if followups_overdue else _("None overdue"),
            "url": reverse("partners:followup_list"),
            "action": _("Open the follow-ups"),
            "urgent": followups_overdue > 0,
        })
    priorities += [
        {
            "rank": 40,
            "count": alerts["verification_stuck"],
            "label": ngettext("Verification stalled", "Verifications stalled", alerts["verification_stuck"]),
            "hint": _("No progress for %(days)s days or more") % {"days": settings_obj.verification_stuck_days},
            "url": f"{affiliates_url}?alert=verification_stuck",
            "action": _("See the affiliates"),
            "urgent": False,
        },
        {
            "rank": 50,
            "count": alerts["registration_stuck"],
            "label": ngettext("Registration stalled", "Registrations stalled", alerts["registration_stuck"]),
            "hint": _("Deriv account not created after %(days)s days") % {"days": settings_obj.registration_stuck_days},
            "url": f"{affiliates_url}?alert=registration_stuck",
            "action": _("See the affiliates"),
            "urgent": False,
        },
        {
            "rank": 60,
            "count": alerts["contact_stale"],
            "label": ngettext("Affiliate without recent contact", "Affiliates without recent contact", alerts["contact_stale"]),
            "hint": _("No contact for %(days)s days or more") % {"days": settings_obj.contact_stale_days},
            "url": f"{affiliates_url}?alert=contact_stale",
            "action": _("See the affiliates"),
            "urgent": False,
        },
    ]
    return {
        "order": 10,
        "template": "partners/dashboard_section.html",
        "priorities": priorities,
        "context": {
            "total": current.count(),
            "active": current.filter(status=Affiliate.Status.ACTIVE).count(),
            "prospects": current.filter(status=Affiliate.Status.PROSPECT).count(),
            "registration_pending": services.registration_pending(visible).count(),
            "verification_pending": services.verification_pending(visible).count(),
            "followups_due": followups_due,
            "followups_open": followups.count(),
            "alerts": alerts,
            "thresholds": settings_obj,
            "can_view_followups": request_has_perm(request, "partners.view_followups"),
        },
    }
