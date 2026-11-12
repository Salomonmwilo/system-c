"""Outils partagés par les fournisseurs du tableau de bord (aucune dépendance aux modules)."""

from __future__ import annotations

import datetime as dt
from bisect import bisect_right

GROWTH_DAYS = 30
PERIODS = (7, 30, 90)


def growth(total: int, previous: int) -> int | None:
    """Évolution en pourcentage par rapport à ``previous`` ; None si la base est nulle."""
    if previous <= 0:
        return None
    return round((total - previous) * 100 / previous)


def period_days(today: dt.date, period: int) -> list[dt.date]:
    return [today - dt.timedelta(days=period - 1 - i) for i in range(period)]


def cumulative(creation_dates: list[dt.date], days: list[dt.date]) -> list[int]:
    """Nombre d'éléments créés au plus tard chaque jour (fin de journée)."""
    ordered = sorted(creation_dates)
    return [bisect_right(ordered, day) for day in days]
