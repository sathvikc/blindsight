"""Map an RGB triple to the nearest human-readable colour name.

A named colour ("navy blue") is far more useful to a language model than a hex
code ("#1A3C5E"), so descriptors carry both. The palette is intentionally small
and description-oriented rather than exhaustive.
"""

from __future__ import annotations

# Curated, description-friendly palette. (name, (r, g, b))
_PALETTE: list[tuple[str, tuple[int, int, int]]] = [
    ("black", (0, 0, 0)),
    ("dark gray", (64, 64, 64)),
    ("gray", (128, 128, 128)),
    ("light gray", (200, 200, 200)),
    ("white", (255, 255, 255)),
    ("red", (220, 20, 20)),
    ("dark red", (120, 0, 0)),
    ("maroon", (100, 30, 40)),
    ("orange", (255, 140, 0)),
    ("gold", (255, 191, 0)),
    ("yellow", (240, 220, 30)),
    ("olive", (128, 128, 0)),
    ("lime green", (110, 200, 40)),
    ("green", (30, 150, 60)),
    ("dark green", (0, 80, 30)),
    ("teal", (0, 128, 128)),
    ("cyan", (0, 200, 200)),
    ("sky blue", (100, 180, 235)),
    ("blue", (30, 80, 200)),
    ("navy blue", (20, 30, 90)),
    ("purple", (128, 0, 160)),
    ("magenta", (200, 30, 160)),
    ("pink", (255, 150, 190)),
    ("brown", (140, 80, 40)),
    ("beige", (225, 200, 160)),
]


def nearest_name(rgb: tuple[int, int, int]) -> str:
    """Return the closest palette colour name by Euclidean distance in RGB."""
    r, g, b = rgb
    best_name = ""
    best_dist = float("inf")
    for name, (pr, pg, pb) in _PALETTE:
        dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name


def to_hex(rgb: tuple[int, int, int]) -> str:
    """Format an RGB triple as ``#RRGGBB``."""
    return "#{:02X}{:02X}{:02X}".format(*rgb)
