"""Image statistics: dimensions, orientation, brightness, contrast, channels."""

from __future__ import annotations

from math import gcd
from typing import Any

import numpy as np

from ..context import ImageContext

NAME = "stats"
TITLE = "Stats"


def _aspect_ratio(width: int, height: int) -> str:
    divisor = gcd(width, height) or 1
    return f"{width // divisor}:{height // divisor}"


def _orientation(width: int, height: int) -> str:
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"


def run(ctx: ImageContext) -> dict[str, Any]:
    gray = ctx.gray
    rgb = ctx.rgb

    mean = float(gray.mean())
    std = float(gray.std())

    brightness = "dark" if mean < 85 else "bright" if mean > 170 else "mid"
    contrast = "low" if std < 40 else "high" if std > 70 else "medium"

    channels = {
        ch: {"mean": round(float(rgb[..., i].mean()), 1),
             "std": round(float(rgb[..., i].std()), 1)}
        for i, ch in enumerate(("r", "g", "b"))
    }

    return {
        "resolution": f"{ctx.width}x{ctx.height}",
        "orientation": _orientation(ctx.width, ctx.height),
        "aspect_ratio": _aspect_ratio(ctx.width, ctx.height),
        "brightness": brightness,
        "contrast": contrast,
        "channels": channels,
    }


def render(data: dict[str, Any]) -> list[str]:
    lines = [
        f"resolution: {data['resolution']}",
        f"orientation: {data['orientation']}",
        f"aspect_ratio: {data['aspect_ratio']}",
        f"brightness: {data['brightness']}",
        f"contrast: {data['contrast']}",
    ]
    return lines
