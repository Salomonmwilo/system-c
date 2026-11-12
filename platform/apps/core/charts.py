"""Géométrie des graphiques du tableau de bord, calculée sur le serveur.

Les gabarits la dessinent en SVG : aucune bibliothèque JavaScript et aucun style
en ligne (seulement des attributs SVG, que la CSP autorise). Règles de la skill
dataviz : trait de 2, aire à 10 % sous la première série, points de rayon 4,
grille en filet, légende dès deux séries, tableau de données pour chaque graphique.
Les coordonnées sont rendues en chaînes (point décimal) : passées comme nombres,
la localisation française des gabarits écrirait « 50,0 », invalide en SVG.
"""

from __future__ import annotations

from dataclasses import dataclass, field

WIDTH = 600
HEIGHT = 200
DOTS_UP_TO = 14  # au-delà, seul le dernier point est marqué
MAX_AXIS_LABELS = 7


def nice_ceiling(value: float) -> int:
    """Plus petit nombre « rond » (1, 2, 5 × 10^n) supérieur ou égal à value ; au moins 1."""
    if value <= 1:
        return 1
    magnitude = 10 ** (len(str(int(value))) - 1)
    for step in (1, 2, 5, 10):
        if step * magnitude >= value:
            return step * magnitude
    return 10 * magnitude


def ticks(ymax: int) -> list[int]:
    """Graduations régulières de 0 à ymax (au plus six)."""
    for parts in (4, 5, 2, 1):
        if ymax % parts == 0:
            step = ymax // parts
            return list(range(0, ymax + 1, step))
    return [0, ymax]


def _n(value: float) -> str:
    return f"{value:.1f}"


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


def smooth_path(xs: list[float], ys: list[float]) -> str:
    if len(xs) < 2:
        xs, ys = [0.0, float(WIDTH)], [ys[0] if ys else float(HEIGHT)] * 2
    tangents = _monotone_tangents(xs, ys)
    parts = [f"M{xs[0]:.1f},{ys[0]:.1f}"]
    for i in range(len(xs) - 1):
        dx = (xs[i + 1] - xs[i]) / 3
        parts.append(
            f"C{xs[i] + dx:.1f},{ys[i] + tangents[i] * dx:.1f} "
            f"{xs[i + 1] - dx:.1f},{ys[i + 1] - tangents[i + 1] * dx:.1f} {xs[i + 1]:.1f},{ys[i + 1]:.1f}"
        )
    return "".join(parts)


@dataclass
class LineChart:
    width: int
    height: int
    ymax: int
    ticks: list[dict]
    series: list[dict]
    points: list[dict]
    axis: list[str]
    rows: list[dict] = field(default_factory=list)


def line_chart(labels: list[str], tips: list[str], series: list[dict], *, width: int = WIDTH, height: int = HEIGHT) -> LineChart:
    """Courbes lissées partageant un axe ; ``series`` : ``[{"label", "values"}]``.

    ``labels`` : libellés courts de l'axe ; ``tips`` : libellé complet de chaque date
    (infobulle et tableau). Une seule échelle pour toutes les séries (jamais deux axes).
    """
    count = len(labels)
    ymax = nice_ceiling(max((v for s in series for v in s["values"]), default=0))
    step = width / max(count - 1, 1)
    xs = [i * step for i in range(count)]

    def y(value: float) -> float:
        return height - (value / ymax) * height

    drawn = []
    for index, item in enumerate(series):
        ys = [y(v) for v in item["values"]]
        line = smooth_path(xs, ys)
        drawn.append({
            "label": item["label"],
            "key": f"s{index + 1}",
            "line": line,
            "area": f"{line}L{xs[-1]:.1f},{height}L{xs[0]:.1f},{height}Z" if index == 0 and count > 1 else "",
            "dots": [{"x": _n(x), "y": _n(v)} for x, v in zip(xs, ys)] if count <= DOTS_UP_TO
            else [{"x": _n(xs[-1]), "y": _n(ys[-1])}],
            "last": item["values"][-1] if item["values"] else 0,
        })
    shown = count if count <= MAX_AXIS_LABELS else MAX_AXIS_LABELS
    keep = {round(j * (count - 1) / max(shown - 1, 1)) for j in range(shown)}
    points = []
    for i in range(count):
        values = [s["values"][i] for s in series]
        readout = " · ".join(f"{s['label']} {v}" for s, v in zip(series, values))
        points.append({
            "index": i,
            "x": _n(xs[i]),
            "hit_x": _n(max(0.0, xs[i] - step / 2)),
            "hit_width": _n(min(width, xs[i] + step / 2) - max(0.0, xs[i] - step / 2)),
            "tip": f"{tips[i]} · {readout}",
        })
    return LineChart(
        width=width,
        height=height,
        ymax=ymax,
        ticks=[{"value": t, "y": _n(y(t))} for t in reversed(ticks(ymax))],
        series=drawn,
        points=points,
        axis=[labels[i] for i in sorted(keep)],
        rows=[{"label": tips[i], "values": [s["values"][i] for s in series]} for i in range(count)],
    )
