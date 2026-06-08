"""Shared image context passed to every module.

Loading and colour-space conversions happen once, here, instead of inside each
module. Modules read whichever representation they need (PIL, RGB, grayscale,
or OpenCV's BGR) without re-decoding the file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image


class ModuleUnavailable(Exception):
    """Raised by a module when an optional dependency or resource is missing.

    The orchestrator turns this into a graceful "unavailable" result rather than
    letting it abort the whole extraction.
    """


@dataclass
class ImageContext:
    """Pre-decoded views of a single image."""

    path: str
    pil: Image.Image          # RGB, PIL Image (keeps EXIF on the original load)
    rgb: np.ndarray           # H x W x 3, uint8, RGB
    gray: np.ndarray          # H x W, uint8
    width: int
    height: int
    # Data from modules that have already run, keyed by module NAME. Lets a
    # later fusion module (e.g. ``layout``) reason over earlier detections
    # without re-running them. Boxes stored here are normalised to [0, 1].
    results: dict[str, Any] = field(default_factory=dict)

    @property
    def bgr(self) -> np.ndarray:
        """OpenCV-ordered (BGR) view of the image."""
        return self.rgb[:, :, ::-1]


def load_context(path: str, max_side: int = 1600) -> ImageContext:
    """Load an image into an :class:`ImageContext`.

    Large images are downscaled so per-pixel operations stay fast; the reported
    width/height remain the original dimensions so callers see the true size.
    EXIF orientation is *not* auto-applied here — the EXIF module reports it
    explicitly instead.
    """
    pil_original = Image.open(path)
    pil_original.load()
    orig_w, orig_h = pil_original.size

    rgb_pil = pil_original.convert("RGB")
    longest = max(rgb_pil.size)
    if longest > max_side:
        scale = max_side / longest
        new_size = (round(rgb_pil.width * scale), round(rgb_pil.height * scale))
        rgb_pil = rgb_pil.resize(new_size, Image.LANCZOS)

    rgb = np.asarray(rgb_pil, dtype=np.uint8)
    # Rec. 601 luma — matches what most CV tooling expects for grayscale.
    gray = np.dot(rgb[..., :3], [0.299, 0.587, 0.114]).astype(np.uint8)

    return ImageContext(
        path=path,
        pil=pil_original,
        rgb=rgb,
        gray=gray,
        width=orig_w,
        height=orig_h,
    )
