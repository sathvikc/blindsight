"""Geometry helpers shared across modules (position and size naming)."""

from __future__ import annotations

_ROWS = ("top", "middle", "bottom")
_COLS = ("left", "center", "right")


def region_name(cx: float, cy: float, width: int, height: int) -> str:
    """Name the 3x3 grid cell a centre point falls in, e.g. ``"top-center"``.

    The middle-center cell is reported simply as ``"center"``.
    """
    col = _COLS[min(2, int(cx / max(width, 1) * 3))]
    row = _ROWS[min(2, int(cy / max(height, 1) * 3))]
    if row == "middle" and col == "center":
        return "center"
    if row == "middle":
        return col
    return f"{row}-{col}"


def size_bucket(area: float, image_area: float) -> str:
    """Bucket an object's area relative to the image into small/medium/large."""
    if image_area <= 0:
        return "unknown"
    frac = area / image_area
    if frac < 0.02:
        return "small"
    if frac < 0.15:
        return "medium"
    return "large"
