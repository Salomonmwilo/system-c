from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"
    verbose_name = _("Core")

    def ready(self):
        from . import signals  # noqa: F401
        from .registry import register_audit_actions

        register_audit_actions({
            "member_created": (_("Member added"), "new"),
            "member_roles_changed": (_("Member roles changed"), "change"),
            "thresholds_changed": (_("Alert thresholds changed"), "change"),
            "password_changed": (_("Password changed"), "access"),
            "platform_bootstrapped": (_("Platform initialised"), "new"),
        })
