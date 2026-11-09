from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BotsConfig(AppConfig):
    name = "apps.bots"
    label = "bots"
    verbose_name = _("Robot management")

    def ready(self):
        from apps.core.registry import register_affiliate_panel, register_dashboard_provider
        from apps.core.services import register_organization_setup

        from .extensions import affiliate_robot_panel, bots_section
        from .services import ensure_parameter_catalog

        register_dashboard_provider(bots_section)
        register_affiliate_panel(affiliate_robot_panel)
        register_organization_setup(ensure_parameter_catalog)
