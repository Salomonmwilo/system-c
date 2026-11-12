from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AcademyConfig(AppConfig):
    name = "apps.academy"
    label = "academy"
    verbose_name = _("Academy")

    def ready(self):
        from apps.core.registry import register_dashboard_provider

        from .dashboard import academy_section

        register_dashboard_provider(academy_section)
