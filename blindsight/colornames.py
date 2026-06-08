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
    ("light blue", (170, 200, 240)),
    ("sky blue", (100, 180, 235)),
    ("blue", (30, 80, 200)),
    ("navy blue", (20, 30, 90)),
    ("purple", (128, 0, 160)),
    ("magenta", (200, 30, 160)),
    ("pink", (255, 150, 190)),
    ("salmon", (230, 150, 140)),
    ("brown", (140, 80, 40)),
    ("dark brown", (80, 50, 35)),
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


# Hue buckets in degrees (lower bound inclusive) -> base name. Names reuse the
# vocabulary of the palette above so accent names read consistently with the
# dominant ones.
_HUE_NAMES: list[tuple[float, str]] = [
    (0, "red"), (15, "orange"), (45, "gold"), (63, "yellow"),
    (75, "lime green"), (95, "green"), (150, "teal"), (180, "cyan"),
    (200, "sky blue"), (225, "blue"), (255, "indigo"), (270, "purple"),
    (300, "magenta"), (330, "pink"), (345, "red"),
]


def _rgb_to_hsv(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """Return (hue 0-360, saturation 0-1, value 0-1) for an RGB triple."""
    r, g, b = (c / 255.0 for c in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    chroma = mx - mn
    if chroma == 0:
        hue = 0.0
    elif mx == r:
        hue = 60 * (((g - b) / chroma) % 6)
    elif mx == g:
        hue = 60 * (((b - r) / chroma) + 2)
    else:
        hue = 60 * (((r - g) / chroma) + 4)
    sat = 0.0 if mx == 0 else chroma / mx
    return hue % 360, sat, mx


def accent_name(rgb: tuple[int, int, int]) -> str:
    """Name a colour by its hue, robust to low saturation.

    Unlike :func:`nearest_name` (pure RGB nearest-neighbour, which can collapse a
    pale hue onto a neutral gray anchor), this routes neutral colours to a
    lightness-based neutral name and chromatic colours to a hue bucket. Used for
    the accent line, where preserving the *hue* of a brand colour is the point.
    """
    hue, sat, val = _rgb_to_hsv(rgb)

    # Neutral: too little saturation to carry a hue -> name by lightness.
    if sat < 0.12:
        if val < 0.18:
            return "black"
        if val < 0.40:
            return "dark gray"
        if val < 0.78:
            return "gray"
        if val < 0.93:
            return "light gray"
        return "white"

    base = "red"
    for lower, name in _HUE_NAMES:
        if hue >= lower:
            base = name
    if val < 0.35:
        return f"dark {base}"
    if sat < 0.45 and val > 0.7:
        return f"light {base}"
    return base
