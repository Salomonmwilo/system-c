from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PartnersConfig(AppConfig):
    name = "apps.partners"
    label = "partners"
    verbose_name = _("Partners")

    def ready(self):
        from apps.core.registry import register_dashboard_provider

        from .dashboard import partners_section

        register_dashboard_provider(partners_section)
