"""Contributions du module bots au tableau de bord et à la fiche affilié."""

from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

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
            "urgent": modification_late > 0,
        },
        {
            "rank": 70,
            "count": review_due,
            "label": ngettext("Configuration to review", "Configurations to review", review_due),
            "hint": _("Declared applied more than %(days)s days ago") % {"days": settings_obj.configuration_review_days},
            "url": f"{bots_url}?alert=configuration_review",
            "action": _("See the robot users"),
            "urgent": False,
        },
    ]
    return {
        "order": 20,
        "template": "bots/dashboard_section.html",
        "priorities": priorities,
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
