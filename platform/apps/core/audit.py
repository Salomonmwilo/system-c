"""Écriture du journal d'audit.

Le résumé ne contient que des identifiants, des énumérations, des noms de champs
et des montants déclarés. Les clés qui ressemblent à des secrets sont retirées,
et les textes sont tronqués : les notes complètes ne sont jamais journalisées.
"""

from __future__ import annotations

import datetime as dt
import decimal
import uuid

from .models import AuditLog

FORBIDDEN_KEY_PARTS = ("token", "password", "passwd", "secret", "api_key", "apikey", "credential", "note")
MAX_TEXT = 120


def _clean_value(value):
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, (decimal.Decimal, float)):
        return str(value)
    if isinstance(value, (uuid.UUID, dt.date, dt.datetime)):
        return str(value)
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_clean_value(v) for v in list(value)[:50]]
    text = str(value)
    return text[:MAX_TEXT]


def sanitize(summary: dict | None) -> dict:
    clean = {}
    for key, value in (summary or {}).items():
        lowered = str(key).lower()
        if any(part in lowered for part in FORBIDDEN_KEY_PARTS):
            continue
        clean[str(key)[:64]] = _clean_value(value)
    return clean


def record(action: str, *, actor=None, organization=None, target=None, **summary) -> AuditLog:
    target_type = ""
    target_id = ""
    if target is not None:
        target_type = f"{target._meta.app_label}.{target._meta.model_name}"
        target_id = str(target.pk)
    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None
    return AuditLog.objects.create(
        organization=organization,
        actor=actor,
        action=action[:64],
        target_type=target_type,
        target_id=target_id,
        summary=sanitize(summary),
    )


def changed_fields(instance, cleaned_data: dict, fields) -> list[str]:
    """Liste des champs dont la valeur change (noms seulement)."""
    changed = []
    for name in fields:
        if name in cleaned_data and getattr(instance, name) != cleaned_data[name]:
            changed.append(name)
    return changed
