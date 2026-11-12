"""Points d'extension entre modules, sans dépendance de core vers les modules.

Chaque module enregistre ses fournisseurs au démarrage (``AppConfig.ready``).
``partners`` affiche ainsi les panneaux fournis par ``bots`` sans jamais
importer ``bots``, ce qui garde le graphe de dépendances sans cycle.
"""

from __future__ import annotations

from collections.abc import Callable

_dashboard_providers: list[Callable] = []
_affiliate_panels: list[Callable] = []


def register_dashboard_provider(provider: Callable) -> Callable:
    if provider not in _dashboard_providers:
        _dashboard_providers.append(provider)
    return provider


def register_affiliate_panel(provider: Callable) -> Callable:
    if provider not in _affiliate_panels:
        _affiliate_panels.append(provider)
    return provider


def dashboard_sections(request) -> list[dict]:
    """Sections du tableau de bord ; chaque fournisseur vérifie ses permissions."""
    sections = [section for provider in _dashboard_providers if (section := provider(request))]
    return sorted(sections, key=lambda s: s.get("order", 100))


def affiliate_panels(request, affiliate_id) -> list[dict]:
    panels = [panel for provider in _affiliate_panels if (panel := provider(request, affiliate_id))]
    return sorted(panels, key=lambda p: p.get("order", 100))


# Recherche globale, cloche de notifications et libellés du journal : chaque module
# fournit les siens, après avoir vérifié ses propres permissions.
_search_providers: list[Callable] = []
_notification_providers: list[Callable] = []
_audit_actions: dict[str, tuple] = {}


def register_search_provider(provider: Callable) -> Callable:
    if provider not in _search_providers:
        _search_providers.append(provider)
    return provider


def register_notification_provider(provider: Callable) -> Callable:
    if provider not in _notification_providers:
        _notification_providers.append(provider)
    return provider


def register_audit_actions(actions: dict[str, tuple]) -> None:
    """``{action: (libellé paresseux, catégorie)}`` ; catégories : new, done, config, change, payment, access."""
    _audit_actions.update(actions)


def search(request, query: str) -> list[dict]:
    """Groupes de résultats ; un fournisseur peut renvoyer un groupe ou une liste de groupes."""
    groups: list[dict] = []
    for provider in _search_providers:
        found = provider(request, query)
        if isinstance(found, dict):
            groups.append(found)
        elif found:
            groups.extend(found)
    return sorted(groups, key=lambda g: g.get("order", 100))


def notifications(request) -> list[dict]:
    items = [item for provider in _notification_providers for item in (provider(request) or [])]
    return sorted(items, key=lambda i: i.get("rank", 100))


def audit_action(action: str) -> tuple:
    return _audit_actions.get(action, (None, "change"))
