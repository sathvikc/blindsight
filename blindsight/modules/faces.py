"""Face detection via OpenCV Haar cascades (classical, no ML model download).

Runs both frontal and profile cascades and merges overlapping hits, so a face
detected by both is not double-counted. This is deliberately conservative: the
descriptor reports presence, count, and rough position, never identity.
"""

from __future__ import annotations

from typing import Any

from ..context import ImageContext, ModuleUnavailable
from ..geometry import region_name

NAME = "faces"
TITLE = "Faces"

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


def _load_cascade(filename: str):
    path = cv2.data.haarcascades + filename
    cascade = cv2.CascadeClassifier(path)
    return None if cascade.empty() else cascade


def _overlaps(a, b, thresh: float = 0.5) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return union > 0 and inter / union > thresh


def run(ctx: ImageContext) -> dict[str, Any]:
    if cv2 is None:
        raise ModuleUnavailable("opencv-python is not installed")

    frontal = _load_cascade("haarcascade_frontalface_default.xml")
    profile = _load_cascade("haarcascade_profileface.xml")
    if frontal is None and profile is None:
        raise ModuleUnavailable("Haar cascade data files not found")

    gray = ctx.gray
    detections: list[tuple[int, int, int, int]] = []
    for cascade in (frontal, profile):
        if cascade is None:
            continue
        hits = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                        minSize=(24, 24))
        for box in hits:
            box = tuple(int(v) for v in box)
            if not any(_overlaps(box, kept) for kept in detections):
                detections.append(box)

    h, w = gray.shape
    positions = [
        region_name(x + bw / 2, y + bh / 2, w, h)
        for (x, y, bw, bh) in detections
    ]

    return {"count": len(detections), "positions": positions}


def render(data: dict[str, Any]) -> list[str]:
    lines = [f"count: {data['count']}"]
    if data["positions"]:
        lines.append("positions: " + ", ".join(data["positions"]))
    return lines
