"""Indicateurs du module partners pour le tableau de bord (données réelles).

Chaque fournisseur renvoie un résumé et des « priorités » : des lignes du registre
« À traiter », triées par le tableau de bord selon leur rang d'urgence.
"""

import datetime as dt

from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth
from django.urls import reverse
from django.utils import dateformat, timezone
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from apps.core.charts import Point, area_chart, bar_chart
from apps.core.models import OrganizationSettings
from apps.core.permissions import request_has_perm

from . import services
from .models import Affiliate, Interaction, TrackEvent


def _month_starts(today: dt.date, count: int) -> list[dt.date]:
    months, year, month = [], today.year, today.month
    for _ in range(count):
        months.append(dt.date(year, month, 1))
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    return months[::-1]


def new_affiliates_by_month(visible, today: dt.date):
    months = _month_starts(today, 12)
    rows = (
        visible.filter(created_at__date__gte=months[0])
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(n=Count("id"))
    )
    counts = {row["month"].date() if hasattr(row["month"], "date") else row["month"]: row["n"] for row in rows}
    return bar_chart([
        Point(
            label=dateformat.format(m, "M"),
            value=counts.get(m, 0),
            tip=ngettext("%(n)s new affiliate in %(month)s", "%(n)s new affiliates in %(month)s", counts.get(m, 0))
            % {"n": counts.get(m, 0), "month": dateformat.format(m, "F Y")},
        )
        for m in months
    ])


def steps_by_week(visible, today: dt.date):
    start = today - dt.timedelta(days=today.weekday()) - dt.timedelta(weeks=7)
    events = TrackEvent.objects.filter(affiliate__in=visible, declared_on__gte=start, declared_on__lte=today).values_list("declared_on", flat=True)
    weeks = [start + dt.timedelta(weeks=i) for i in range(8)]
    counts = {w: 0 for w in weeks}
    for day in events:
        counts[day - dt.timedelta(days=day.weekday())] += 1
    return bar_chart([
        Point(
            label=dateformat.format(w, "j/m"),
            value=counts[w],
            tip=ngettext("%(n)s step declared in the week of %(date)s", "%(n)s steps declared in the week of %(date)s", counts[w])
            % {"n": counts[w], "date": dateformat.format(w, "j F")},
        )
        for w in weeks
    ])


def interactions_by_day(visible, today: dt.date):
    start = today - dt.timedelta(days=29)
    rows = (
        Interaction.objects.filter(affiliate__in=visible, occurred_at__date__gte=start)
        .annotate(day=TruncDate("occurred_at"))
        .values("day")
        .annotate(n=Count("id"))
    )
    counts = {row["day"]: row["n"] for row in rows}
    days = [start + dt.timedelta(days=i) for i in range(30)]
    return area_chart([
        Point(
            label=dateformat.format(d, "j/m"),
            value=counts.get(d, 0),
            tip=ngettext("%(n)s interaction on %(date)s", "%(n)s interactions on %(date)s", counts.get(d, 0))
            % {"n": counts.get(d, 0), "date": dateformat.format(d, "j F")},
        )
        for d in days
    ])


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
    current_count = current.count()
    active_count = current.filter(status=Affiliate.Status.ACTIVE).count()
    verified_count = current.filter(verification_status=Affiliate.Verification.VALIDATED).count()
    kpis = [
        {
            "rank": 10,
            "label": _("Active affiliates"),
            "value": active_count,
            "total": current_count,
            "hint": ngettext("of %(n)s affiliate", "of %(n)s affiliates", current_count) % {"n": current_count},
            "url": f"{affiliates_url}?status=active",
        },
        {
            "rank": 20,
            "label": _("Verified Deriv accounts"),
            "value": verified_count,
            "total": current_count,
            "hint": _("declared, not checked with Deriv"),
            "declared": True,
            "url": affiliates_url,
        },
    ]
    widgets = [
        {"slot": "main", "order": 30, "template": "partners/dashboard_new_affiliates.html",
         "context": {"chart": new_affiliates_by_month(visible, today)}},
        {"slot": "side", "order": 10, "template": "partners/dashboard_steps.html",
         "context": {"chart": steps_by_week(visible, today)}},
        {"slot": "side", "order": 30, "template": "partners/dashboard_interactions.html",
         "context": {"chart": interactions_by_day(visible, today)}},
    ]
    return {
        "order": 10,
        "template": "partners/dashboard_section.html",
        "priorities": priorities,
        "kpis": kpis,
        "widgets": widgets,
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
