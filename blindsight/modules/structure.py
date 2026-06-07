"""Edge and structural layout: edge density, dominant line orientations, layout.

Uses OpenCV's Canny + probabilistic Hough transform. Canny thresholds are
derived from the image's own median intensity so the module adapts to dark and
bright images alike instead of relying on fixed magic numbers.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..context import ImageContext, ModuleUnavailable

NAME = "structure"
TITLE = "Structure"

try:
    import cv2
except ImportError:  # pragma: no cover - exercised only without OpenCV
    cv2 = None


def _auto_canny(gray: np.ndarray, sigma: float = 0.33) -> np.ndarray:
    median = float(np.median(gray))
    lower = int(max(0, (1.0 - sigma) * median))
    upper = int(min(255, (1.0 + sigma) * median))
    return cv2.Canny(gray, lower, max(upper, lower + 1))


def _classify_lines(lines: np.ndarray | None) -> dict[str, bool]:
    found = {"horizontal": False, "vertical": False, "diagonal": False}
    if lines is None:
        return found
    for x1, y1, x2, y2 in lines[:, 0]:
        angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1))) % 180
        if angle < 20 or angle > 160:
            found["horizontal"] = True
        elif 70 < angle < 110:
            found["vertical"] = True
        else:
            found["diagonal"] = True
    return found


def run(ctx: ImageContext) -> dict[str, Any]:
    if cv2 is None:
        raise ModuleUnavailable("opencv-python is not installed")

    edges = _auto_canny(ctx.gray)
    edge_ratio = float((edges > 0).mean())
    density = "low" if edge_ratio < 0.05 else "high" if edge_ratio > 0.12 else "medium"

    min_len = max(20, min(ctx.gray.shape) // 8)
    raw = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=80,
        minLineLength=min_len, maxLineGap=10,
    )
    lines = _classify_lines(raw)
    line_count = 0 if raw is None else int(len(raw))

    if density == "high" or line_count > 40:
        layout = "busy"
    elif any(lines.values()):
        layout = "structured"
    else:
        layout = "minimal"

    return {
        "edge_density": density,
        "edge_ratio": round(edge_ratio, 3),
        "lines": lines,
        "line_count": line_count,
        "layout": layout,
    }


def render(data: dict[str, Any]) -> list[str]:
    lines = data["lines"]
    flags = ", ".join(f"{k}={str(v).lower()}" for k, v in lines.items())
    return [
        f"edge_density: {data['edge_density']}",
        f"lines: {flags}",
        f"layout: {data['layout']}",
    ]
