"""Shape and contour analysis: count, classify, size, and locate regions.

Contours come from auto-thresholded edges. Each significant contour is reduced
with Douglas-Peucker (``approxPolyDP``) and classified by vertex count and
circularity. Tiny noise contours are filtered by relative area.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..context import ImageContext, ModuleUnavailable
from ..geometry import region_name, size_bucket

NAME = "shapes"
TITLE = "Shapes"

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

_MIN_AREA_FRAC = 0.005   # ignore contours smaller than 0.5% of the image
_MAX_SHAPES = 12


def _classify(contour: np.ndarray) -> str:
    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
    verts = len(approx)
    area = cv2.contourArea(contour)

    if verts == 3:
        return "triangle"
    if verts == 4:
        _, (w, h), _ = cv2.minAreaRect(contour)
        ratio = max(w, h) / max(min(w, h), 1)
        return "square" if ratio < 1.2 else "rectangle"
    # Circularity: 1.0 for a perfect circle, lower for jagged shapes.
    circularity = 4 * np.pi * area / max(perimeter ** 2, 1)
    if circularity > 0.75:
        return "circle"
    if verts < 3:
        return "blob"
    return f"polygon({verts})"


def run(ctx: ImageContext) -> dict[str, Any]:
    if cv2 is None:
        raise ModuleUnavailable("opencv-python is not installed")

    h, w = ctx.gray.shape
    image_area = float(h * w)
    min_area = image_area * _MIN_AREA_FRAC

    blurred = cv2.GaussianBlur(ctx.gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    shapes: list[dict[str, Any]] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        moments = cv2.moments(contour)
        if moments["m00"] == 0:
            continue
        cx = moments["m10"] / moments["m00"]
        cy = moments["m01"] / moments["m00"]
        shapes.append({
            "shape": _classify(contour),
            "size": size_bucket(area, image_area),
            "position": region_name(cx, cy, w, h),
            "area_frac": round(area / image_area, 3),
        })

    # A huge irregular polygon/blob is almost always several touching objects
    # merged into one outline by edge dilation, not a real shape — reporting
    # "polygon(7), large, center" only invites the model to hallucinate an
    # object. Named shapes (rectangle, circle, ...) are kept at any size.
    shapes = [
        s for s in shapes
        if s["area_frac"] < 0.15
        or not (s["shape"].startswith("polygon") or s["shape"] == "blob")
    ]

    shapes.sort(key=lambda s: s["area_frac"], reverse=True)
    shapes = shapes[:_MAX_SHAPES]

    return {"count": len(shapes), "shapes": shapes}


def render(data: dict[str, Any]) -> list[str]:
    if data["count"] == 0:
        return ["count: 0"]
    lines = [f"count: {data['count']}"]
    for s in data["shapes"]:
        lines.append(f"- {s['shape']}, {s['size']}, {s['position']}")
    return lines
