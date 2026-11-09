"""Services communs de core."""

from collections.abc import Callable

_organization_setup_hooks: list[Callable] = []


def register_organization_setup(hook: Callable) -> Callable:
    """Permet à un module de préparer ses données pour une nouvelle organisation."""
    if hook not in _organization_setup_hooks:
        _organization_setup_hooks.append(hook)
    return hook


def run_organization_setup(organization) -> None:
    for hook in _organization_setup_hooks:
        hook(organization)
