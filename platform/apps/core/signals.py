from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from . import audit


@receiver(user_logged_in)
def audit_login(sender, request, user, **kwargs):
    audit.record("login", actor=user, organization=getattr(request, "organization", None), target=user)


@receiver(user_logged_out)
def audit_logout(sender, request, user, **kwargs):
    if user is not None:
        audit.record("logout", actor=user, organization=getattr(request, "organization", None), target=user)
