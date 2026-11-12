from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AcademyConfig(AppConfig):
    name = "apps.academy"
    label = "academy"
    verbose_name = _("Academy")

    def ready(self):
        from apps.core.registry import (
            register_audit_actions,
            register_dashboard_provider,
            register_notification_provider,
            register_search_provider,
        )

        from .dashboard import AUDIT_ACTIONS, academy_notifications, academy_search, academy_section

        register_dashboard_provider(academy_section)
        register_notification_provider(academy_notifications)
        register_search_provider(academy_search)
        register_audit_actions(AUDIT_ACTIONS)
