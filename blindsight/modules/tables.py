"""Ruled-table reconstruction: grid geometry plus per-cell text.

Tables are the densest factual payload an image can carry, and the place where flat OCR output fails hardest — a spreadsheet read as one word soup loses exactly the row/column associations the numbers depend on. This module recovers those associations classically: morphological opening with long thin kernels isolates ruling lines, the line positions define a cell grid, and one Tesseract pass over the table assigns each word to its cell by geometry. The output is rows of pipe-separated cells — the format text models already read as a table.

Only *ruled* tables are reconstructed. Whitespace-aligned columns without ruling lines are deliberately out of scope: inferring an invisible grid is exactly the kind of invented structure this project refuses to emit (the OCR module's line/paragraph output still carries such text faithfully). Several gates keep false positives out — a grid needs at least three ruling lines each way (a lone rectangle is not a table), the lines must span the grid, and their crossings must actually exist in ink.
"""

from __future__ import annotations

from bisect import bisect_right
from typing import Any

import numpy as np

from ..context import ImageContext, ModuleUnavailable
from ..geometry import region_name

NAME = "tables"
TITLE = "Tables"

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

try:
    import pytesseract
    from pytesseract import Output
except ImportError:  # pragma: no cover
    pytesseract = None
    Output = None

# A ruling line must be long relative to the image for the morphological
# opening to keep it; text strokes and underlines are shorter than this.
_MIN_LINE_FRAC = 30  # kernel length = image extent / this

# A kept line must span most of its table's bbox — partial strokes that
# happen to be long (a horizon, an underline) don't produce a grid.
_MIN_SPAN = 0.6

# Structural gates: >=3 lines each way (>=2x2 cells), and at least this
# fraction of the implied line crossings must exist in ink. Parallel lines
# that never cross (lined paper + a window frame) are not a table.
_MIN_LINES = 3
_MIN_CROSSINGS = 0.7
_CROSSING_WINDOW = 4  # px tolerance around a crossing point

_MAX_TABLES = 3       # report the biggest few; a mosaic of grids is noise
_MAX_CELLS = 400      # a denser "grid" than this is texture, not a table

# Every cell must be at least this many working-copy pixels tall and wide.
# Bold display text passes the line gates — glyph strokes are long, straight,
# and they cross — but the "cells" they imply are a few pixels across. No
# readable table has cells that small.
_MIN_CELL_PX = 10
_MAX_RENDER_ROWS = 12
_MAX_CELL_CHARS = 24


def _line_mask(binary: np.ndarray, horizontal: bool) -> np.ndarray:
    """Keep only long straight runs in one direction via open-with-long-kernel."""
    h, w = binary.shape
    if horizontal:
        size = (max(w // _MIN_LINE_FRAC, 10), 1)
    else:
        size = (1, max(h // _MIN_LINE_FRAC, 10))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, size)
    return cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)


def _line_positions(mask: np.ndarray, span_extent: int, axis: int) -> list[int]:
    """Cluster a line mask into distinct ruling-line positions.

    Sums the mask across ``axis`` and keeps positions where the run covers at least ``_MIN_SPAN`` of the crossing extent; adjacent positions (a line several pixels thick) collapse to their centre.
    """
    coverage = (mask > 0).sum(axis=axis)
    hits = np.nonzero(coverage >= _MIN_SPAN * span_extent)[0]
    if len(hits) == 0:
        return []
    lines: list[int] = []
    start = prev = int(hits[0])
    for pos in hits[1:]:
        pos = int(pos)
        if pos - prev > 2:  # new line once the gap exceeds line thickness
            lines.append((start + prev) // 2)
            start = pos
        prev = pos
    lines.append((start + prev) // 2)
    return lines


def _crossings_exist(h_mask: np.ndarray, v_mask: np.ndarray,
                     ys: list[int], xs: list[int]) -> bool:
    """Verify the implied grid crossings are actually inked."""
    h, w = h_mask.shape
    found = 0
    for y in ys:
        y0, y1 = max(0, y - _CROSSING_WINDOW), min(h, y + _CROSSING_WINDOW + 1)
        for x in xs:
            x0, x1 = max(0, x - _CROSSING_WINDOW), min(w, x + _CROSSING_WINDOW + 1)
            if h_mask[y0:y1, x0:x1].any() and v_mask[y0:y1, x0:x1].any():
                found += 1
    return found >= _MIN_CROSSINGS * len(ys) * len(xs)


def _cell_texts(ctx: ImageContext, bbox: tuple[int, int, int, int],
                ys: list[int], xs: list[int],
                work_w: int, work_h: int) -> list[list[str]] | None:
    """One Tesseract pass over the table crop; words fall into cells by centre.

    Returns ``None`` when OCR is unavailable — the grid geometry is still worth reporting without text. The crop is taken from the full-resolution original (``ctx.pil``), not the downscaled working copy, so small cell text keeps its pixels.
    """
    if pytesseract is None:
        return None
    x0, y0, x1, y1 = bbox
    full_w, full_h = ctx.pil.size
    crop = ctx.pil.convert("RGB").crop((
        int(x0 / work_w * full_w), int(y0 / work_h * full_h),
        int(x1 / work_w * full_w), int(y1 / work_h * full_h),
    ))
    if crop.width < 8 or crop.height < 8:
        return None
    try:
        data = pytesseract.image_to_data(crop, output_type=Output.DICT)
    except Exception:
        return None

    # Cell boundaries as fractions of the table, so words located in the
    # full-resolution crop bucket without any further coordinate juggling.
    row_bounds = [(y - y0) / max(y1 - y0, 1) for y in ys[1:-1]]
    col_bounds = [(x - x0) / max(x1 - x0, 1) for x in xs[1:-1]]
    rows, cols = len(ys) - 1, len(xs) - 1
    cells: list[list[list[str]]] = [[[] for _ in range(cols)] for _ in range(rows)]

    for i, text in enumerate(data["text"]):
        text = text.strip()
        if not text or float(data["conf"][i]) < 0:
            continue
        cx = (data["left"][i] + data["width"][i] / 2) / max(crop.width, 1)
        cy = (data["top"][i] + data["height"][i] / 2) / max(crop.height, 1)
        cells[bisect_right(row_bounds, cy)][bisect_right(col_bounds, cx)].append(text)

    return [[" ".join(cell) for cell in row] for row in cells]


def run(ctx: ImageContext) -> dict[str, Any]:
    if cv2 is None:
        raise ModuleUnavailable("opencv-python is not installed")

    h, w = ctx.gray.shape
    # Inverted adaptive threshold: ruling lines become foreground and uneven
    # lighting (photographed documents) doesn't split a line in two.
    binary = cv2.adaptiveThreshold(
        ctx.gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV, 15, 10)
    h_mask = _line_mask(binary, horizontal=True)
    v_mask = _line_mask(binary, horizontal=False)

    grid = cv2.dilate(h_mask | v_mask,
                      cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    n_labels, _labels, comp_stats, _centroids = \
        cv2.connectedComponentsWithStats(grid)

    candidates = sorted(
        range(1, n_labels),
        key=lambda i: int(comp_stats[i, cv2.CC_STAT_AREA]), reverse=True)

    tables: list[dict[str, Any]] = []
    for label in candidates:
        if len(tables) >= _MAX_TABLES:
            break
        x0 = int(comp_stats[label, cv2.CC_STAT_LEFT])
        y0 = int(comp_stats[label, cv2.CC_STAT_TOP])
        x1 = x0 + int(comp_stats[label, cv2.CC_STAT_WIDTH])
        y1 = y0 + int(comp_stats[label, cv2.CC_STAT_HEIGHT])
        if (x1 - x0) < w * 0.1 or (y1 - y0) < h * 0.05:
            continue  # too small to be a readable table

        h_local = h_mask[y0:y1, x0:x1]
        v_local = v_mask[y0:y1, x0:x1]
        ys = [y0 + p for p in _line_positions(h_local, x1 - x0, axis=1)]
        xs = [x0 + p for p in _line_positions(v_local, y1 - y0, axis=0)]
        if len(ys) < _MIN_LINES or len(xs) < _MIN_LINES:
            continue
        if (len(ys) - 1) * (len(xs) - 1) > _MAX_CELLS:
            continue
        if (min(b - a for a, b in zip(ys, ys[1:])) < _MIN_CELL_PX
                or min(b - a for a, b in zip(xs, xs[1:])) < _MIN_CELL_PX):
            continue
        if not _crossings_exist(h_mask, v_mask, ys, xs):
            continue

        cells = _cell_texts(ctx, (x0, y0, x1, y1), ys, xs, w, h)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        tables.append({
            "rows": len(ys) - 1,
            "cols": len(xs) - 1,
            "position": region_name(cx, cy, w, h),
            "bbox": [round(x0 / w, 3), round(y0 / h, 3),
                     round(x1 / w, 3), round(y1 / h, 3)],
            "cells": cells,
        })

    tables.sort(key=lambda t: t["bbox"][1])  # report in reading order
    return {"count": len(tables), "tables": tables}


def _clip(text: str) -> str:
    return text if len(text) <= _MAX_CELL_CHARS else text[:_MAX_CELL_CHARS - 1] + "…"


def render(data: dict[str, Any]) -> list[str]:
    if data["count"] == 0:
        return []
    lines: list[str] = [f"count: {data['count']}"]
    for n, table in enumerate(data["tables"], start=1):
        lines.append(
            f"table {n}: {table['rows']} rows x {table['cols']} cols "
            f"({table['position']}, ruled)")
        cells = table["cells"]
        if cells is None:
            lines.append("  cells: text unavailable (tesseract missing)")
            continue
        for row in cells[:_MAX_RENDER_ROWS]:
            lines.append("  | " + " | ".join(_clip(c) for c in row) + " |")
        if len(cells) > _MAX_RENDER_ROWS:
            lines.append(f"  … (+{len(cells) - _MAX_RENDER_ROWS} more rows)")
    return lines
