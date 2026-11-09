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
