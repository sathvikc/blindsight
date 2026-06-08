"""Colour analysis: dominant palette, 3x3 colour grid, grayscale detection.

Dominant colours come from Pillow's built-in median-cut quantiser rather than an
extra dependency. Every colour is reported with both a hex code and a
human-readable name, since the name is what an LLM reasons with most reliably.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image

from ..colornames import accent_name, nearest_name, to_hex
from ..context import ImageContext

NAME = "colors"
TITLE = "Colors"

_MAX_PALETTE = 8
_MIN_COVERAGE = 0.04  # drop colours covering < 4% of the image
_ACCENT_MIN_COVERAGE = 0.004  # an accent must still cover > 0.4% to be real
_ACCENT_MIN_CHROMA = 45  # max-min channel spread; below this it is ~neutral


def _is_grayscale(rgb: np.ndarray) -> bool:
    # Largest per-pixel spread between channels; tiny spread => effectively gray.
    spread = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)
    return float(spread.mean()) < 10.0


def _palette_bins(pil: Image.Image) -> list[tuple[tuple[int, int, int], float]]:
    """Quantise once and return [(rgb, coverage), ...] for every palette bin."""
    small = pil.convert("RGB")
    small.thumbnail((200, 200), Image.LANCZOS)
    quantized = small.quantize(colors=_MAX_PALETTE, method=Image.MEDIANCUT)

    palette = quantized.getpalette() or []
    counts = np.bincount(
        np.asarray(quantized, dtype=np.int64).ravel(),
        minlength=_MAX_PALETTE,
    )
    total = counts.sum() or 1

    bins: list[tuple[tuple[int, int, int], float]] = []
    for index, count in enumerate(counts):
        if count == 0:
            continue
        rgb = tuple(int(c) for c in palette[index * 3 : index * 3 + 3])
        if len(rgb) != 3:
            continue
        bins.append((rgb, count / total))
    return bins


def _dominant_colors(bins: list[tuple[tuple[int, int, int], float]]) -> list[dict[str, Any]]:
    colors: list[dict[str, Any]] = []
    for rgb, coverage in bins:
        if coverage < _MIN_COVERAGE:
            continue
        colors.append({
            "hex": to_hex(rgb),
            "name": nearest_name(rgb),
            "coverage": round(float(coverage), 3),
        })
    colors.sort(key=lambda c: c["coverage"], reverse=True)
    return colors[:5]


def _accent_colors(
    bins: list[tuple[tuple[int, int, int], float]],
    dominant: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Chromatic colours that fall *below* the dominant floor.

    A brand colour that owns little area (an amber logo mark on white, a thin
    cyan rule) never reaches the dominant list, yet "what colour is this?" often
    hinges on it. We surface such colours separately, ranked by area, skipping
    any whose hue is already represented among the dominant colours.
    """
    dominant_names = {c["name"] for c in dominant}
    accents: list[dict[str, Any]] = []
    for rgb, coverage in bins:
        if coverage >= _MIN_COVERAGE or coverage < _ACCENT_MIN_COVERAGE:
            continue
        if (max(rgb) - min(rgb)) < _ACCENT_MIN_CHROMA:
            continue  # effectively neutral, not a colour accent
        if nearest_name(rgb) in dominant_names:
            continue  # already covered by a dominant colour of the same hue
        accents.append({
            "hex": to_hex(rgb),
            "name": accent_name(rgb),
            "coverage": round(float(coverage), 3),
        })
    accents.sort(key=lambda c: c["coverage"], reverse=True)
    return accents[:2]


def _grid(rgb: np.ndarray) -> list[list[dict[str, str]]]:
    h, w = rgb.shape[:2]
    ys = np.linspace(0, h, 4, dtype=int)
    xs = np.linspace(0, w, 4, dtype=int)
    grid: list[list[dict[str, str]]] = []
    for r in range(3):
        row: list[dict[str, str]] = []
        for c in range(3):
            cell = rgb[ys[r]:ys[r + 1], xs[c]:xs[c + 1]]
            mean_rgb = tuple(int(v) for v in cell.reshape(-1, 3).mean(axis=0))
            row.append({"hex": to_hex(mean_rgb), "name": nearest_name(mean_rgb)})
        grid.append(row)
    return grid


def run(ctx: ImageContext) -> dict[str, Any]:
    bins = _palette_bins(ctx.pil)
    dominant = _dominant_colors(bins)
    return {
        "dominant": dominant,
        "accent": _accent_colors(bins, dominant),
        "grid": _grid(ctx.rgb),
        "grayscale": _is_grayscale(ctx.rgb),
    }


def render(data: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    dominant = data["dominant"]
    if dominant:
        parts = [f"{c['name']} {c['hex']} ({int(c['coverage'] * 100)}%)"
                 for c in dominant]
        lines.append("dominant: " + ", ".join(parts))

    accent = data.get("accent") or []
    if accent:
        def _pct(cov: float) -> str:
            return f"{int(cov * 100)}%" if cov >= 0.01 else "<1%"
        parts = [f"{c['name']} {c['hex']} ({_pct(c['coverage'])})"
                 for c in accent]
        lines.append("accent: " + ", ".join(parts))

    labels = ("TL", "TC", "TR", "ML", "MC", "MR", "BL", "BC", "BR")
    flat = [cell for row in data["grid"] for cell in row]
    lines.append("grid:")
    for i in range(0, 9, 3):
        triple = "  ".join(
            f"{labels[i + j]}:{flat[i + j]['name']}" for j in range(3)
        )
        lines.append(f"  {triple}")

    lines.append(f"grayscale: {str(data['grayscale']).lower()}")
    return lines
