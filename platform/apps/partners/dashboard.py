"""Indicateurs du module partners pour le tableau de bord (données réelles).

Chaque fournisseur renvoie un résumé et des « priorités » : des lignes du registre
« À traiter », triées par le tableau de bord selon leur rang d'urgence.
"""

import datetime as dt

from django.db.models import Q
from django.urls import reverse
from django.utils.http import urlencode
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.utils.translation import ngettext, npgettext

from apps.core.dashboard import GROWTH_DAYS, growth
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
            "icon": "clock",
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
            "icon": "pencil-square",
            "urgent": False,
        },
        {
            "rank": 50,
            "count": alerts["registration_stuck"],
            "label": ngettext("Registration stalled", "Registrations stalled", alerts["registration_stuck"]),
            "hint": _("Deriv account not created after %(days)s days") % {"days": settings_obj.registration_stuck_days},
            "url": f"{affiliates_url}?alert=registration_stuck",
            "action": _("See the affiliates"),
            "icon": "shield-exclamation",
            "urgent": False,
        },
        {
            "rank": 60,
            "count": alerts["contact_stale"],
            "label": ngettext("Affiliate without recent contact", "Affiliates without recent contact", alerts["contact_stale"]),
            "hint": _("No contact for %(days)s days or more") % {"days": settings_obj.contact_stale_days},
            "url": f"{affiliates_url}?alert=contact_stale",
            "action": _("See the affiliates"),
            "icon": "chat-dots",
            "urgent": False,
        },
    ]
    total = current.count()
    active = current.filter(status=Affiliate.Status.ACTIVE).count()
    month_ago = timezone.now() - dt.timedelta(days=GROWTH_DAYS)
    card = {
        "order": 10,
        "key": "affiliates",
        "icon": "people",
        "title": _("Affiliates"),
        "url": affiliates_url,
        "total": total,
        "total_label": _("Total affiliates"),
        "growth": growth(total, current.filter(created_at__lte=month_ago).count()),
        "split": [
            {"value": active, "label": npgettext("count", "Active", "Active", active), "tone": "ok",
             "url": f"{affiliates_url}?status=active"},
            {"value": total - active, "label": npgettext("count", "Not active", "Not active", total - active), "tone": "muted",
             "url": affiliates_url},
        ],
        "illustration": "img/illustration-affiliates.svg",
    }
    shortcuts = []
    if request_has_perm(request, "partners.add_affiliate"):
        shortcuts.append({"order": 10, "icon": "person-plus", "label": _("Add an affiliate"),
                          "url": reverse("partners:affiliate_create"), "tone": "taupe"})
    if request_has_perm(request, "partners.view_followups"):
        shortcuts.append({"order": 30, "icon": "bell", "label": _("See the follow-ups"),
                          "url": reverse("partners:followup_list"), "tone": "ochre"})
    return {
        "order": 10,
        "priorities": priorities,
        "kpis": [{"rank": 10, "icon": "people", "value": total, "label": _("Affiliates"), "url": affiliates_url}],
        "card": card,
        "shortcuts": shortcuts,
        "series": [{
            "rank": 10,
            "label": _("Affiliates (total)"),
            "dates": [d.date() for d in current.values_list("created_at", flat=True)],
        }],
        "context": {
            "total": total,
            "active": active,
            "prospects": current.filter(status=Affiliate.Status.PROSPECT).count(),
            "registration_pending": services.registration_pending(visible).count(),
            "verification_pending": services.verification_pending(visible).count(),
            "followups_due": followups_due,
            "followups_open": followups.count(),
            "alerts": alerts,
        },
    }


def partners_notifications(request):
    """Cloche : relances échues (aujourd'hui ou en retard) visibles par l'utilisateur."""
    if not request_has_perm(request, "partners.view_followups"):
        return []
    due = services.open_followups(request).filter(due_on__lte=timezone.localdate()).count()
    if not due:
        return []
    return [{
        "rank": 10,
        "count": due,
        "label": ngettext("%(n)s follow-up to do", "%(n)s follow-ups to do", due) % {"n": due},
        "url": reverse("partners:followup_list"),
        "icon": "clock",
    }]


def partners_search(request, query):
    if not request_has_perm(request, "partners.view_affiliate"):
        return None
    terms = Q(display_name__icontains=query)
    if request_has_perm(request, "partners.view_pii"):
        terms |= Q(email__icontains=query) | Q(phone__icontains=query)
    found = services.visible_affiliates(request).filter(terms).order_by("display_name")
    results = [
        {
            "title": affiliate.display_name,
            "meta": affiliate.get_status_display() + (f" · {_('Archived')}" if affiliate.archived_at else ""),
            "url": reverse("partners:affiliate_detail", args=[affiliate.pk]),
        }
        for affiliate in found[:8]
    ]
    return {
        "order": 10,
        "title": _("Affiliates"),
        "icon": "people",
        "results": results,
        "total": found.count(),
        "more_url": f"{reverse('partners:affiliate_list')}?{urlencode({'q': query})}",
    }


AUDIT_ACTIONS = {
    "affiliate_created": (gettext_lazy("Affiliate record created"), "new"),
    "affiliate_updated": (gettext_lazy("Affiliate record updated"), "change"),
    "affiliate_archived": (gettext_lazy("Affiliate record archived"), "change"),
    "affiliate_track_recorded": (gettext_lazy("Deriv step recorded"), "change"),
    "interaction_added": (gettext_lazy("Interaction recorded"), "done"),
    "followup_created": (gettext_lazy("Follow-up planned"), "new"),
    "followup_closed": (gettext_lazy("Follow-up closed"), "done"),
    "referral_link_created": (gettext_lazy("Referral link created"), "new"),
    "referral_link_toggled": (gettext_lazy("Referral link switched on or off"), "change"),
}
