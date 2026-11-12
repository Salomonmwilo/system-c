"""Géométrie des graphiques du tableau de bord, calculée sur le serveur.

Les gabarits la dessinent en SVG : aucune bibliothèque JavaScript et aucun style
en ligne (seulement des attributs SVG, que la CSP autorise). Règles de la skill
dataviz : barres de 24 unités au plus, extrémité arrondie de 4 et base carrée,
trait de 2, aire à 10 % d'opacité, point final de rayon 4, grille en filet.
Les libellés sont en HTML, sous le graphique, pour garder leur taille réelle.
Les coordonnées sont rendues en chaînes (point décimal) : passées comme nombres,
la localisation française des gabarits écrirait « 50,0 », invalide en SVG.
"""

from __future__ import annotations

from dataclasses import dataclass, field

WIDTH = 600
HEIGHT = 140
BAR_MAX = 24
RADIUS = 4


def nice_ceiling(value: float) -> int:
    """Plus petit nombre « rond » (1, 2, 5 × 10^n) supérieur ou égal à value ; au moins 1."""
    if value <= 1:
        return 1
    magnitude = 10 ** (len(str(int(value))) - 1)
    for step in (1, 2, 5, 10):
        if step * magnitude >= value:
            return step * magnitude
    return 10 * magnitude


def _n(value: float) -> str:
    return f"{value:.1f}"


def column_path(x: float, top: float, width: float, base: float, radius: float = RADIUS) -> str:
    """Colonne à extrémité arrondie et base carrée (aucune bordure, aucun contour)."""
    height = base - top
    r = min(radius, height, width / 2)
    return (
        f"M{x:.1f},{base:.1f}V{top + r:.1f}"
        f"Q{x:.1f},{top:.1f} {x + r:.1f},{top:.1f}"
        f"H{x + width - r:.1f}"
        f"Q{x + width:.1f},{top:.1f} {x + width:.1f},{top + r:.1f}"
        f"V{base:.1f}Z"
    )


@dataclass
class Point:
    label: str  # libellé court sous l'axe
    value: float
    tip: str  # texte complet de l'infobulle et du tableau


@dataclass
class BarChart:
    width: int
    height: int
    ymax: int
    bars: list[dict] = field(default_factory=list)
    total: float = 0


def bar_chart(points: list[Point], *, highlight_last: bool = True, width: int = WIDTH, height: int = HEIGHT) -> BarChart:
    """Colonnes d'une seule série ; la dernière (période en cours) porte l'accent."""
    ymax = nice_ceiling(max((p.value for p in points), default=0))
    band = width / max(len(points), 1)
    bar_width = min(BAR_MAX, band * 0.6)
    chart = BarChart(width=width, height=height, ymax=ymax, total=sum(p.value for p in points))
    for index, point in enumerate(points):
        x = index * band + (band - bar_width) / 2
        top = height - (point.value / ymax) * (height - 2)
        chart.bars.append({
            "path": column_path(x, top, bar_width, height) if point.value > 0 else "",
            "hit_x": _n(index * band),
            "hit_width": _n(band),
            "label": point.label,
            "value": point.value,
            "tip": point.tip,
            "current": highlight_last and index == len(points) - 1,
        })
    return chart


def _monotone_tangents(xs: list[float], ys: list[float]) -> list[float]:
    """Tangentes de Fritsch-Carlson : la courbe ne dépasse jamais les valeurs réelles."""
    n = len(xs)
    slopes = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    tangents = [slopes[0]] + [
        0.0 if slopes[i - 1] * slopes[i] <= 0 else (slopes[i - 1] + slopes[i]) / 2 for i in range(1, n - 1)
    ] + [slopes[-1]]
    for i, slope in enumerate(slopes):
        if slope == 0:
            tangents[i] = tangents[i + 1] = 0.0
            continue
        a, b = tangents[i] / slope, tangents[i + 1] / slope
        s = a * a + b * b
        if s > 9:
            t = 3 / s ** 0.5
            tangents[i], tangents[i + 1] = t * a * slope, t * b * slope
    return tangents


@dataclass
class AreaChart:
    width: int
    height: int
    ymax: int
    line: str
    area: str
    end_x: str
    end_y: str
    points: list[dict]
    total: float


def area_chart(points: list[Point], *, width: int = WIDTH, height: int = HEIGHT) -> AreaChart:
    """Courbe lissée sans dépassement, aire légère dessous, point sur la dernière valeur."""
    ymax = nice_ceiling(max((p.value for p in points), default=0))
    step = width / max(len(points) - 1, 1)
    pad = RADIUS + 2  # le point final reste entier dans le cadre
    xs = [i * step for i in range(len(points))]
    ys = [height - pad - (p.value / ymax) * (height - 2 * pad) for p in points]
    if len(points) < 2:
        xs, ys = [0, width], [ys[0] if ys else height - pad] * 2
    tangents = _monotone_tangents(xs, ys)
    path = [f"M{xs[0]:.1f},{ys[0]:.1f}"]
    for i in range(len(xs) - 1):
        dx = (xs[i + 1] - xs[i]) / 3
        path.append(
            f"C{xs[i] + dx:.1f},{ys[i] + tangents[i] * dx:.1f} "
            f"{xs[i + 1] - dx:.1f},{ys[i + 1] - tangents[i + 1] * dx:.1f} {xs[i + 1]:.1f},{ys[i + 1]:.1f}"
        )
    line = "".join(path)
    return AreaChart(
        width=width,
        height=height,
        ymax=ymax,
        line=line,
        area=f"{line}L{xs[-1]:.1f},{height}L{xs[0]:.1f},{height}Z",
        end_x=_n(xs[-1]),
        end_y=_n(ys[-1]),
        # Zone de survol : tout l'intervalle autour du point, pas seulement le trait.
        points=[
            {
                "x": _n(x),
                "hit_x": _n(max(0.0, x - step / 2)),
                "hit_width": _n(min(width, x + step / 2) - max(0.0, x - step / 2)),
                "label": p.label,
                "value": p.value,
                "tip": p.tip,
            }
            for x, p in zip(xs, points)
        ],
        total=sum(p.value for p in points),
    )
