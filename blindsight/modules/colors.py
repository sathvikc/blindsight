"""Colour analysis: dominant palette, 3x3 colour grid, grayscale detection.

Dominant colours come from Pillow's built-in median-cut quantiser rather than an
extra dependency. Every colour is reported with both a hex code and a
human-readable name, since the name is what an LLM reasons with most reliably.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image

from ..colornames import nearest_name, to_hex
from ..context import ImageContext

NAME = "colors"
TITLE = "Colors"

_MAX_PALETTE = 8
_MIN_COVERAGE = 0.04  # drop colours covering < 4% of the image


def _is_grayscale(rgb: np.ndarray) -> bool:
    # Largest per-pixel spread between channels; tiny spread => effectively gray.
    spread = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)
    return float(spread.mean()) < 10.0


def _dominant_colors(pil: Image.Image) -> list[dict[str, Any]]:
    small = pil.convert("RGB")
    small.thumbnail((200, 200), Image.LANCZOS)
    quantized = small.quantize(colors=_MAX_PALETTE, method=Image.MEDIANCUT)

    palette = quantized.getpalette() or []
    counts = np.bincount(
        np.asarray(quantized, dtype=np.int64).ravel(),
        minlength=_MAX_PALETTE,
    )
    total = counts.sum() or 1

    colors: list[dict[str, Any]] = []
    for index, count in enumerate(counts):
        coverage = count / total
        if coverage < _MIN_COVERAGE:
            continue
        rgb = tuple(int(c) for c in palette[index * 3 : index * 3 + 3])
        if len(rgb) != 3:
            continue
        colors.append({
            "hex": to_hex(rgb),
            "name": nearest_name(rgb),
            "coverage": round(float(coverage), 3),
        })

    colors.sort(key=lambda c: c["coverage"], reverse=True)
    return colors[:5]


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
    return {
        "dominant": _dominant_colors(ctx.pil),
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
