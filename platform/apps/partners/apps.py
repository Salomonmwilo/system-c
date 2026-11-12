from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PartnersConfig(AppConfig):
    name = "apps.partners"
    label = "partners"
    verbose_name = _("Partners")

    def ready(self):
        from apps.core.registry import (
            register_audit_actions,
            register_dashboard_provider,
            register_notification_provider,
            register_search_provider,
        )

        from .dashboard import AUDIT_ACTIONS, partners_notifications, partners_search, partners_section

        register_dashboard_provider(partners_section)
        register_notification_provider(partners_notifications)
        register_search_provider(partners_search)
        register_audit_actions(AUDIT_ACTIONS)
