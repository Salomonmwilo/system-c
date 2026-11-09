"""Outils partagés par les tests : organisations, comptes avec rôles, requêtes."""

from __future__ import annotations

import itertools

from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory

from apps.core.middleware import SESSION_KEY
from apps.core.models import Membership, Organization, OrganizationSettings, Role, User
from apps.core.services import run_organization_setup

PASSWORD = "Test-Password-2026!"
_counter = itertools.count(1)


def make_org(name: str | None = None) -> Organization:
    number = next(_counter)
    org = Organization.objects.create(name=name or f"Organisation {number}", slug=f"org-{number}")
    OrganizationSettings.for_organization(org)
    run_organization_setup(org)
    return org


def make_user(org: Organization | None = None, *roles: str, email: str | None = None, language: str = "fr") -> User:
    number = next(_counter)
    user = User.objects.create_user(
        email=email or f"user{number}@example.org",
        password=PASSWORD,
        full_name=f"Utilisateur {number}",
        preferred_language=language,
    )
    for role in roles:
        Membership.objects.create(user=user, organization=org, role=role)
    return user


def login(client, user: User, org: Organization | None = None) -> None:
    client.force_login(user)
    if org is not None:
        session = client.session
        session[SESSION_KEY] = str(org.pk)
        session.save()


def fake_request(user: User, org: Organization, path: str = "/"):
    """Requête minimale pour appeler directement les services (permissions comprises)."""
    request = RequestFactory().post(path)
    request.user = user
    request.session = SessionStore()
    request.organization = org
    request.org_roles = frozenset(
        Membership.objects.filter(user=user, organization=org).values_list("role", flat=True)
    )
    return request


ALL_ROLES = [choice for choice, _label in Role.choices]
