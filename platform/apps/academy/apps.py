from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AcademyConfig(AppConfig):
    name = "apps.academy"
    label = "academy"
    verbose_name = _("Academy")
