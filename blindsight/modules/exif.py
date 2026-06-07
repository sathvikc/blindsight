"""EXIF metadata: capture date, device, GPS presence, orientation.

GPS coordinates are reduced to a presence flag rather than exact location — the
descriptor is meant to inform an LLM, not to leak precise positions by default.
"""

from __future__ import annotations

from typing import Any

from PIL.ExifTags import GPSTAGS, TAGS

from ..context import ImageContext

NAME = "exif"
TITLE = "EXIF"

_ORIENTATION_LANDSCAPE = {1, 2, 3, 4}


def run(ctx: ImageContext) -> dict[str, Any]:
    exif = ctx.pil.getexif()
    if not exif:
        return {"present": False}

    tags = {TAGS.get(k, k): v for k, v in exif.items()}

    make = str(tags.get("Make", "")).strip()
    model = str(tags.get("Model", "")).strip()
    device = " ".join(p for p in (make, model) if p) or None

    date = tags.get("DateTime") or tags.get("DateTimeOriginal")
    date = str(date).split(" ")[0].replace(":", "-") if date else None

    orientation_code = tags.get("Orientation")
    orientation = None
    if orientation_code:
        orientation = ("landscape" if orientation_code in _ORIENTATION_LANDSCAPE
                       else "portrait")

    gps = exif.get_ifd(0x8825) if hasattr(exif, "get_ifd") else None
    has_gps = bool(gps)

    present = any((device, date, orientation, has_gps))
    return {
        "present": present,
        "date": date,
        "device": device,
        "gps": "available" if has_gps else None,
        "orientation": orientation,
    }


def render(data: dict[str, Any]) -> list[str]:
    if not data.get("present"):
        return ["none"]
    lines = []
    for key in ("date", "device", "gps", "orientation"):
        if data.get(key):
            lines.append(f"{key}: {data[key]}")
    return lines or ["none"]
