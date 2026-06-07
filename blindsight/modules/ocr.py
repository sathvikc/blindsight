"""Text extraction (OCR) via Tesseract.

Optional module. It degrades gracefully to "unavailable" when either the
``pytesseract`` Python package or the system ``tesseract`` binary is missing,
so the rest of the descriptor is unaffected. Word-level confidences are
aggregated into a single reliability hint, and the dominant text block's
position and relative size are reported.
"""

from __future__ import annotations

from typing import Any

from ..context import ImageContext, ModuleUnavailable
from ..geometry import region_name

NAME = "ocr"
TITLE = "OCR"

try:
    import pytesseract
    from pytesseract import Output
except ImportError:  # pragma: no cover
    pytesseract = None
    Output = None


def _size_label(height: int, image_height: int) -> str:
    frac = height / max(image_height, 1)
    if frac < 0.03:
        return "small"
    if frac < 0.08:
        return "medium"
    return "large"


def run(ctx: ImageContext) -> dict[str, Any]:
    if pytesseract is None:
        raise ModuleUnavailable("pytesseract is not installed (pip install pytesseract)")

    try:
        data = pytesseract.image_to_data(ctx.pil, output_type=Output.DICT)
    except (pytesseract.TesseractNotFoundError, EnvironmentError) as exc:
        raise ModuleUnavailable(f"tesseract binary not available: {exc}") from exc

    words: list[str] = []
    confidences: list[float] = []
    heights: list[int] = []
    centers: list[tuple[float, float]] = []

    for i, text in enumerate(data["text"]):
        text = text.strip()
        conf = float(data["conf"][i])
        if not text or conf < 0:
            continue
        words.append(text)
        confidences.append(conf)
        heights.append(int(data["height"][i]))
        centers.append((
            data["left"][i] + data["width"][i] / 2,
            data["top"][i] + data["height"][i] / 2,
        ))

    if not words:
        return {"text": "", "word_count": 0, "confidence": None,
                "position": None, "size": None}

    full_text = " ".join(words)
    avg_conf = round(sum(confidences) / len(confidences), 1)

    # Locate and size the largest text element as a representative anchor.
    biggest = heights.index(max(heights))
    cx, cy = centers[biggest]
    position = region_name(cx, cy, ctx.rgb.shape[1], ctx.rgb.shape[0])
    size = _size_label(heights[biggest], ctx.rgb.shape[0])

    return {
        "text": full_text,
        "word_count": len(words),
        "confidence": avg_conf,
        "position": position,
        "size": size,
    }


def render(data: dict[str, Any]) -> list[str]:
    if data["word_count"] == 0:
        return ["text: (none detected)"]
    reliability = "reliable" if (data["confidence"] or 0) >= 75 else "uncertain"
    return [
        f'text: "{data["text"]}"',
        f"confidence: {data['confidence']}% ({reliability})",
        f"position: {data['position']}",
        f"size: {data['size']}",
    ]
