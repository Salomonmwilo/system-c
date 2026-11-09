"""Contributions du module bots au tableau de bord et à la fiche affilié."""

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
    return {
        "order": 20,
        "template": "bots/dashboard_section.html",
        "context": {
            "total": queryset.exclude(status=BotStatus.DISABLED).count(),
            "to_apply": services.to_apply(queryset).count(),
            "modification_requested": counts[BotStatus.MODIFICATION_REQUESTED],
            "applied": counts[BotStatus.APPLIED],
            "paused": counts[BotStatus.PAUSED],
            "disabled": counts[BotStatus.DISABLED],
            "real": queryset.filter(current_account_type="real").exclude(status=BotStatus.DISABLED).count(),
            "alerts": {
                "modification_pending": services.modification_pending(queryset, settings_obj).count(),
                "configuration_review": services.configuration_review_due(queryset, settings_obj).count(),
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
