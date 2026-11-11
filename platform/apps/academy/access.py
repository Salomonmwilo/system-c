"""Règle d'accès aux contenus d'Academy, évaluée côté serveur.

Une ressource est accessible si elle est publiée et :
- soit gratuite (visibilité « public »), sans achat ni compte ;
- soit incluse dans l'offre d'une inscription active de la personne.

Une inscription active donne accès seulement si elle n'a pas expiré et, quand
elle provient d'une commande, si cette commande est payée et confirmée. Une
offre ne donne que les ressources qui lui sont rattachées : Complete n'ouvre pas
ce qui est réservé à Guided.
"""

from django.db.models import Q
from django.utils import timezone

from .models import Enrollment, Order, Resource


def active_enrollments(user, program):
    if user is None or not user.is_authenticated:
        return Enrollment.objects.none()
    return (
        Enrollment.objects.filter(
            user=user,
            program=program,
            organization_id=program.organization_id,
            status=Enrollment.Status.ACTIVE,
        )
        .filter(Q(access_until__isnull=True) | Q(access_until__gt=timezone.now()))
        .filter(Q(order__isnull=True) | Q(order__status=Order.Status.PAID))
    )


def can_access_resource(user, resource: Resource) -> bool:
    if resource.status != Resource.Status.PUBLISHED or not resource.has_content:
        return False
    if resource.visibility == Resource.Visibility.PUBLIC:
        return True
    offer_ids = active_enrollments(user, resource.program).exclude(offer__isnull=True).values("offer_id")
    return resource.offers.filter(pk__in=offer_ids).exists()
