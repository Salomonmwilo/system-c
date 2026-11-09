from .models import Membership, Organization

SESSION_KEY = "systemc_organization_id"

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "form-action 'self'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
    ]
)
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"


class SecurityHeadersMiddleware:
    """Ajoute la CSP et la Permissions-Policy (Django 5.2 ne fournit pas de CSP)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        if getattr(request, "user", None) is not None and request.user.is_authenticated:
            # Les pages privées ne doivent pas être mises en cache.
            response.headers.setdefault("Cache-Control", "no-store")
        return response


def _resolve(request):
    """Détermine l'organisation courante parmi celles dont l'utilisateur est membre."""
    request.organization = None
    request.org_roles = frozenset()
    request.user_organizations = []
    user = request.user
    if not user.is_authenticated:
        return
    organizations = list(
        Organization.objects.filter(is_active=True, memberships__user=user).distinct().order_by("name")
    )
    request.user_organizations = organizations
    if not organizations:
        return
    wanted = request.session.get(SESSION_KEY)
    current = next((org for org in organizations if str(org.pk) == wanted), None)
    if current is None:
        current = organizations[0]
        request.session[SESSION_KEY] = str(current.pk)
    request.organization = current
    request.org_roles = frozenset(
        Membership.objects.filter(user=user, organization=current).values_list("role", flat=True)
    )


class OrganizationMiddleware:
    """Expose ``request.organization`` et ``request.org_roles`` (organisation courante)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _resolve(request)
        return self.get_response(request)


__all__ = ["OrganizationMiddleware", "SecurityHeadersMiddleware", "SESSION_KEY"]
