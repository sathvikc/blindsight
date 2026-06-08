"""Text extraction (OCR) via Tesseract.

Optional module. It degrades gracefully to "unavailable" when either the
``pytesseract`` Python package or the system ``tesseract`` binary is missing,
so the rest of the descriptor is unaffected. Word-level confidences are
aggregated into a single reliability hint, and the dominant text block's
position and relative size are reported.

Words are reassembled in reading order from Tesseract's block/paragraph/line
indices rather than raw detection order, and line structure is preserved in the
output. When a first pass is low-confidence *and already found text*, a second
pass on an upscaled, thresholded image is tried and kept only if it scores
higher — a refinement that never runs on text-free images, so honest negatives
(a photo with no text) are never turned into hallucinated text.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np
from PIL import Image

from ..context import ImageContext, ModuleUnavailable
from ..geometry import region_name

NAME = "ocr"
TITLE = "OCR"

_LOW_CONF = 75.0  # below this a refinement pass is attempted
_UPSCALE = 2.0    # magnification for the refinement pass

try:
    import pytesseract
    from pytesseract import Output
except ImportError:  # pragma: no cover
    pytesseract = None
    Output = None


def _size_label(height: float, image_height: int) -> str:
    frac = height / max(image_height, 1)
    if frac < 0.03:
        return "small"
    if frac < 0.08:
        return "medium"
    return "large"


def _extract_words(pil: Image.Image) -> list[dict[str, Any]]:
    """Run Tesseract on one image and return kept word records."""
    data = pytesseract.image_to_data(pil, output_type=Output.DICT)
    words: list[dict[str, Any]] = []
    for i, text in enumerate(data["text"]):
        text = text.strip()
        conf = float(data["conf"][i])
        if not text or conf < 0:
            continue
        words.append({
            "text": text,
            "conf": conf,
            "left": int(data["left"][i]),
            "top": int(data["top"][i]),
            "width": int(data["width"][i]),
            "height": int(data["height"][i]),
            "line": (int(data["block_num"][i]),
                     int(data["par_num"][i]),
                     int(data["line_num"][i])),
        })
    return words


def _order_lines(words: list[dict[str, Any]]) -> list[str]:
    """Reassemble words into reading-ordered lines.

    Words are grouped by their (block, paragraph, line) key, ordered left to
    right within a line, and the lines themselves ordered top to bottom. This is
    robust to Tesseract emitting detections out of spatial order.
    """
    grouped: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    for w in words:
        grouped.setdefault(w["line"], []).append(w)

    records: list[tuple[int, int, str]] = []
    for ws in grouped.values():
        ws.sort(key=lambda w: w["left"])
        top = min(w["top"] for w in ws)
        left = min(w["left"] for w in ws)
        records.append((top, left, " ".join(w["text"] for w in ws)))

    records.sort(key=lambda r: (r[0], r[1]))
    return [text for _, _, text in records]


def _preprocess(pil: Image.Image) -> Image.Image:
    """Upscale + Otsu-threshold an image to help marginal, small, or faint text."""
    gray = cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
    up = cv2.resize(gray, None, fx=_UPSCALE, fy=_UPSCALE,
                    interpolation=cv2.INTER_CUBIC)
    _t, binar = cv2.threshold(up, 0, 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(binar)


def _conf_mass(words: list[dict[str, Any]]) -> float:
    return sum(w["conf"] for w in words)


def run(ctx: ImageContext) -> dict[str, Any]:
    if pytesseract is None:
        raise ModuleUnavailable("pytesseract is not installed (pip install pytesseract)")

    try:
        words = _extract_words(ctx.pil)
    except (pytesseract.TesseractNotFoundError, EnvironmentError) as exc:
        raise ModuleUnavailable(f"tesseract binary not available: {exc}") from exc

    scale = 1.0
    # Refinement pass: only when the first pass already found text but is shaky.
    # Never runs on text-free images, so honest negatives stay negatives.
    if words and (_conf_mass(words) / len(words)) < _LOW_CONF:
        try:
            alt = _extract_words(_preprocess(ctx.pil))
        except Exception:  # pragma: no cover - refinement is best-effort
            alt = []
        if alt and _conf_mass(alt) > _conf_mass(words):
            words, scale = alt, _UPSCALE

    if not words:
        return {"text": "", "lines": [], "word_count": 0,
                "confidence": None, "position": None, "size": None}

    line_texts = _order_lines(words)
    avg_conf = round(_conf_mass(words) / len(words), 1)

    # Per-word boxes normalised to [0, 1], for the layout fusion module. Pixel
    # coords are mapped back through ``scale`` (refinement upscale) and the
    # original image dimensions so every module's boxes share one coordinate space.
    img_w, img_h = ctx.pil.size
    word_boxes = [
        {
            "text": w["text"],
            "conf": w["conf"],
            "box": (
                (w["left"] / scale) / max(img_w, 1),
                (w["top"] / scale) / max(img_h, 1),
                (w["width"] / scale) / max(img_w, 1),
                (w["height"] / scale) / max(img_h, 1),
            ),
        }
        for w in words
    ]

    # Locate and size the largest text element as a representative anchor,
    # mapping coordinates back to the original image scale.
    biggest = max(words, key=lambda w: w["height"])
    cx = (biggest["left"] + biggest["width"] / 2) / scale
    cy = (biggest["top"] + biggest["height"] / 2) / scale
    position = region_name(cx, cy, ctx.rgb.shape[1], ctx.rgb.shape[0])
    size = _size_label(biggest["height"] / scale, ctx.rgb.shape[0])

    return {
        "text": " ".join(line_texts),
        "lines": line_texts,
        "word_count": len(words),
        "confidence": avg_conf,
        "position": position,
        "size": size,
        "words": word_boxes,
    }


def render(data: dict[str, Any]) -> list[str]:
    if data["word_count"] == 0:
        return ["text: (none detected)"]
    reliability = "reliable" if (data["confidence"] or 0) >= 75 else "uncertain"
    lines = data.get("lines") or [data["text"]]
    text_repr = " / ".join(lines)
    return [
        f'text: "{text_repr}"',
        f"confidence: {data['confidence']}% ({reliability})",
        f"position: {data['position']}",
        f"size: {data['size']}",
    ]
