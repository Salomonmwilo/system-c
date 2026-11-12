"""Contributions du module bots au tableau de bord et à la fiche affilié."""

import datetime as dt

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
from .models import BotStatus, BotUser


def bots_section(request):
    if not request_has_perm(request, "bots.view_botuser"):
        return None
    settings_obj = OrganizationSettings.for_organization(request.organization)
    queryset = BotUser.objects.filter(organization=request.organization)
    counts = {status: 0 for status in BotStatus.values}
    for row in queryset.values("status").order_by():
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    to_apply = services.to_apply(queryset).count()
    modification_requested = counts[BotStatus.MODIFICATION_REQUESTED]
    modification_late = services.modification_pending(queryset, settings_obj).count()
    review_due = services.configuration_review_due(queryset, settings_obj).count()
    bots_url = reverse("bots:botuser_list")
    priorities = [
        {
            "rank": 20,
            "count": to_apply,
            "label": ngettext("Configuration to apply on the VPS", "Configurations to apply on the VPS", to_apply),
            "hint": _("Robot users waiting for their first applied configuration"),
            "url": f"{bots_url}?alert=to_apply",
            "action": _("See the robot users"),
            "icon": "gear",
            "urgent": False,
        },
        {
            "rank": 30,
            "count": modification_requested,
            "label": ngettext("Change waiting to be applied", "Changes waiting to be applied", modification_requested),
            "hint": ngettext(
                "%(n)s waiting for more than %(days)s days",
                "%(n)s waiting for more than %(days)s days",
                modification_late,
            ) % {"n": modification_late, "days": settings_obj.modification_pending_days}
            if modification_late else _("None beyond the alert threshold"),
            "url": f"{bots_url}?status=modification_requested",
            "action": _("See the robot users"),
            "icon": "gear-wide-connected",
            "urgent": modification_late > 0,
        },
        {
            "rank": 70,
            "count": review_due,
            "label": ngettext("Configuration to review", "Configurations to review", review_due),
            "hint": _("Declared applied more than %(days)s days ago") % {"days": settings_obj.configuration_review_days},
            "url": f"{bots_url}?alert=configuration_review",
            "action": _("See the robot users"),
            "icon": "arrow-repeat",
            "urgent": False,
        },
    ]
    total = sum(counts.values())
    month_ago = timezone.now() - dt.timedelta(days=GROWTH_DAYS)
    card = {
        "order": 20,
        "key": "bots",
        "icon": "robot",
        "title": _("Robot users"),
        "url": bots_url,
        "total": total,
        "total_label": _("Declared robot users"),
        "growth": growth(total, queryset.filter(created_at__lte=month_ago).count()),
        "split": [
            {"value": counts[BotStatus.APPLIED],
             "label": npgettext("count", "Applied", "Applied", counts[BotStatus.APPLIED]), "tone": "ok",
             "url": f"{bots_url}?status={BotStatus.APPLIED}"},
            {"value": counts[BotStatus.DISABLED], "label": npgettext("count", "Disabled", "Disabled", counts[BotStatus.DISABLED]),
             "tone": "muted", "url": f"{bots_url}?status={BotStatus.DISABLED}"},
        ],
        "declared": _("statuses declared, not checked on the VPS"),
        "illustration": "img/illustration-robot.svg",
    }
    shortcuts = [{"order": 20, "icon": "gear", "label": _("Apply a configuration"),
                  "url": f"{bots_url}?alert=to_apply", "tone": "plum"}]
    return {
        "order": 20,
        "priorities": priorities,
        "kpis": [
            {"rank": 20, "icon": "robot", "value": counts_active(counts), "label": _("Robot users"), "url": bots_url},
            {"rank": 30, "icon": "stack", "value": counts[BotStatus.APPLIED], "label": _("Configurations applied"),
             "url": f"{bots_url}?status={BotStatus.APPLIED}", "declared": True},
        ],
        "card": card,
        "shortcuts": shortcuts,
        "series": [{
            "rank": 20,
            "label": _("Robot users"),
            "dates": [d.date() for d in queryset.values_list("created_at", flat=True)],
        }],
        "context": {
            "total": queryset.exclude(status=BotStatus.DISABLED).count(),
            "to_apply": to_apply,
            "modification_requested": modification_requested,
            "applied": counts[BotStatus.APPLIED],
            "paused": counts[BotStatus.PAUSED],
            "disabled": counts[BotStatus.DISABLED],
            "real": queryset.filter(current_account_type="real").exclude(status=BotStatus.DISABLED).count(),
            "alerts": {
                "modification_pending": modification_late,
                "configuration_review": review_due,
            },
            "thresholds": settings_obj,
        },
    }


def counts_active(counts):
    """Fiches robot hors fiches désactivées."""
    return sum(n for status, n in counts.items() if status != BotStatus.DISABLED)


def bots_notifications(request):
    """Cloche : configurations à appliquer et modifications en attente."""
    if not request_has_perm(request, "bots.view_botuser"):
        return []
    queryset = BotUser.objects.filter(organization=request.organization)
    waiting = services.to_apply(queryset).count() + queryset.filter(status=BotStatus.MODIFICATION_REQUESTED).count()
    if not waiting:
        return []
    return [{
        "rank": 20,
        "count": waiting,
        "label": ngettext("%(n)s configuration to apply", "%(n)s configurations to apply", waiting) % {"n": waiting},
        "url": f"{reverse('bots:botuser_list')}?alert=to_apply",
        "icon": "gear",
    }]


def bots_search(request, query):
    if not request_has_perm(request, "bots.view_botuser"):
        return None
    found = (
        BotUser.objects.filter(organization=request.organization, affiliate__display_name__icontains=query)
        .select_related("affiliate")
        .order_by("affiliate__display_name")
    )
    results = [
        {
            "title": bot.affiliate.display_name,
            "meta": " · ".join(filter(None, [bot.get_robot_type_display(), bot.get_status_display()])),
            "url": reverse("bots:botuser_detail", args=[bot.pk]),
        }
        for bot in found[:8]
    ]
    return {
        "order": 20,
        "title": _("Robot users"),
        "icon": "robot",
        "results": results,
        "total": found.count(),
        "more_url": f"{reverse('bots:botuser_list')}?{urlencode({'q': query})}",
    }


AUDIT_ACTIONS = {
    "bot_user_created": (gettext_lazy("Robot record created"), "new"),
    "bot_user_updated": (gettext_lazy("Robot record updated"), "change"),
    "bot_user_status_changed": (gettext_lazy("Robot status changed"), "config"),
    "configuration_declared_applied": (gettext_lazy("Configuration declared applied"), "config"),
    "declaration_corrected": (gettext_lazy("Declaration corrected"), "config"),
    "real_account_declared": (gettext_lazy("Real account declared"), "config"),
    "parameter_catalog_changed": (gettext_lazy("Allowed parameters changed"), "config"),
    "version_drafted": (gettext_lazy("Configuration draft created"), "config"),
    "version_draft_updated": (gettext_lazy("Configuration draft updated"), "config"),
    "version_draft_deleted": (gettext_lazy("Configuration draft deleted"), "config"),
    "version_validated": (gettext_lazy("Configuration version validated"), "config"),
}


def affiliate_robot_panel(request, affiliate_id):
    if not request_has_perm(request, "bots.view_botuser"):
        return None
    bot_user = BotUser.objects.filter(organization=request.organization, affiliate_id=affiliate_id).first()
    return {
        "order": 10,
        "template": "bots/affiliate_panel.html",
        "context": {
            "bot_user": bot_user,
            "affiliate_id": affiliate_id,
            "can_add": request_has_perm(request, "bots.add_botuser"),
        },
    }
