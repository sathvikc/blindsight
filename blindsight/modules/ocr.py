"""Text extraction (OCR) via Tesseract.

Optional module. It degrades gracefully to "unavailable" when either the ``pytesseract`` Python package or the system ``tesseract`` binary is missing, so the rest of the descriptor is unaffected. Word-level confidences are aggregated into a single reliability hint, and the dominant text block's position and relative size are reported.

Words are reassembled in reading order from Tesseract's block/paragraph/line indices rather than raw detection order; line *and* paragraph structure are preserved in the output, and side-by-side blocks (columns) are kept contiguous instead of interleaved.

Hard images get extra candidate passes, each targeting a specific classical failure mode:

- **binarized** — upscale + Otsu threshold, for small or faint text; - **inverted** — for light text on a dark background (slides, terminals), attempted only when the image is actually dark; - **deskewed** — for tilted scans and photographed documents, attempted only when the ink's minimum-area rectangle shows a measurable, plausible tilt.

A candidate replaces the first pass only if it scores strictly higher on total confidence mass. When the first pass found *nothing*, a candidate is accepted only with strong evidence (several words at solid confidence), so honest negatives — a photo with no text — are never turned into hallucinated text by the extra passes.
"""

from __future__ import annotations

from typing import Any, Callable, Iterator

import cv2
import numpy as np
from PIL import Image

from ..context import ImageContext, ModuleUnavailable
from ..geometry import region_name

NAME = "ocr"
TITLE = "OCR"

_LOW_CONF = 75.0   # below this mean confidence, candidate passes are attempted
_UPSCALE = 2.0     # magnification for the binarized/inverted passes

# Light-on-dark text implies a dark image; the inverted pass is only attempted
# below this mean luminance so bright, text-free photos never get an extra
# chance to hallucinate.
_DARK_MEAN = 110.0

# Deskew bounds: below the minimum Tesseract copes natively and rotation would
# only blur the glyphs; above the maximum the minAreaRect estimate itself is
# the likely error, so we refuse to guess.
_DESKEW_MIN_DEG = 2.0
_DESKEW_MAX_DEG = 30.0
_MIN_INK_PIXELS = 200  # fewer ink pixels than this cannot support a skew estimate

# Rescue bar: a candidate pass starting from zero first-pass words must clear
# this to be believed. Tesseract on textureless noise produces scattered
# low-confidence fragments; genuine recovered text produces several words at
# solid confidence. This is what keeps "no text" answers honest.
_RESCUE_MIN_WORDS = 2
_RESCUE_MIN_CONF = 60.0

try:
    import pytesseract
    from pytesseract import Output
except ImportError:  # pragma: no cover
    pytesseract = None
    Output = None

# Maps a candidate-pass point back into original image coordinates.
PointMapper = Callable[[float, float], tuple[float, float]]


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


def _order_lines(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reassemble words into reading-ordered lines.

    Words are grouped by their (block, paragraph, line) key and ordered left to right within a line. Lines are then ordered block-first: blocks sort by their top-left corner, and lines sort spatially *within* their block. For a single column this is identical to a plain top-to-bottom sort; for side-by-side columns it keeps each column contiguous instead of interleaving the two texts line by line.

    Each record carries a ``para`` key (block, paragraph) so callers can recover paragraph structure from the flat line list.
    """
    grouped: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    for w in words:
        grouped.setdefault(w["line"], []).append(w)

    records: list[dict[str, Any]] = []
    for key, ws in grouped.items():
        ws.sort(key=lambda w: w["left"])
        records.append({
            "text": " ".join(w["text"] for w in ws),
            "left": min(w["left"] for w in ws),
            "top": min(w["top"] for w in ws),
            "right": max(w["left"] + w["width"] for w in ws),
            "bottom": max(w["top"] + w["height"] for w in ws),
            "para": key[:2],
        })

    block_bbox: dict[int, tuple[int, int]] = {}
    for r in records:
        block = r["para"][0]
        top, left = block_bbox.get(block, (r["top"], r["left"]))
        block_bbox[block] = (min(top, r["top"]), min(left, r["left"]))

    records.sort(key=lambda r: (*block_bbox[r["para"][0]], r["top"], r["left"]))
    return records


def _paragraphs(line_records: list[dict[str, Any]]) -> list[list[str]]:
    """Group ordered line texts into their Tesseract paragraphs."""
    paras: list[list[str]] = []
    current_key: tuple[int, int] | None = None
    for r in line_records:
        if r["para"] != current_key:
            paras.append([])
            current_key = r["para"]
        paras[-1].append(r["text"])
    return paras


def _to_gray(pil: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)


def _map_words(words: list[dict[str, Any]],
               mapper: PointMapper) -> list[dict[str, Any]]:
    """Rewrite word boxes from candidate-pass space into original space.

    All four corners are mapped and re-boxed, which stays exact for scaling and gives the axis-aligned hull under rotation — close enough at the small angles the deskew pass permits for layout linking to keep working.
    """
    mapped: list[dict[str, Any]] = []
    for w in words:
        corners = [
            mapper(w["left"], w["top"]),
            mapper(w["left"] + w["width"], w["top"]),
            mapper(w["left"], w["top"] + w["height"]),
            mapper(w["left"] + w["width"], w["top"] + w["height"]),
        ]
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        mapped.append({**w,
                       "left": int(min(xs)), "top": int(min(ys)),
                       "width": int(max(xs) - min(xs)),
                       "height": int(max(ys) - min(ys))})
    return mapped


def _binarized_pass(gray: np.ndarray,
                    invert: bool) -> tuple[Image.Image, PointMapper]:
    """Upscale + Otsu-threshold, optionally inverting light-on-dark text."""
    src = 255 - gray if invert else gray
    up = cv2.resize(src, None, fx=_UPSCALE, fy=_UPSCALE,
                    interpolation=cv2.INTER_CUBIC)
    _t, binar = cv2.threshold(up, 0, 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(binar), lambda x, y: (x / _UPSCALE, y / _UPSCALE)


def _estimate_skew(gray: np.ndarray) -> float | None:
    """Estimate page tilt from the ink pixels' minimum-area rectangle.

    Ink is the minority side of an Otsu split (text covers less area than its page). The rectangle's angle is normalised into (-45°, 45°] — covering both OpenCV angle conventions — and returned as the correction to feed to ``cv2.getRotationMatrix2D``. ``None`` means "no measurable, trustworthy tilt": too little ink, too small an angle, or one too large to believe.
    """
    _t, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    white_frac = float((bw == 255).mean())
    ink = (bw == 255) if white_frac < 0.5 else (bw == 0)
    ys, xs = np.nonzero(ink)
    if len(xs) < _MIN_INK_PIXELS:
        return None
    pts = np.column_stack([xs, ys]).astype(np.float32)
    angle = float(cv2.minAreaRect(pts)[-1])
    if angle > 45:
        angle -= 90
    elif angle < -45:
        angle += 90
    if not (_DESKEW_MIN_DEG <= abs(angle) <= _DESKEW_MAX_DEG):
        return None
    return angle


def _deskew_pass(gray: np.ndarray,
                 angle: float) -> tuple[Image.Image, PointMapper]:
    """Rotate the page level, expanding the canvas so no text is cropped."""
    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)
    matrix[0, 2] += new_w / 2 - w / 2
    matrix[1, 2] += new_h / 2 - h / 2
    # Fill the exposed corners with the median luminance (≈ page background)
    # so they don't read as huge dark shapes.
    bg = int(np.median(gray))
    rotated = cv2.warpAffine(gray, matrix, (new_w, new_h),
                             flags=cv2.INTER_CUBIC, borderValue=bg)
    inverse = cv2.invertAffineTransform(matrix)

    def mapper(x: float, y: float) -> tuple[float, float]:
        return (inverse[0, 0] * x + inverse[0, 1] * y + inverse[0, 2],
                inverse[1, 0] * x + inverse[1, 1] * y + inverse[1, 2])

    return Image.fromarray(rotated), mapper


def _candidates(gray: np.ndarray) -> Iterator[tuple[str, Image.Image, PointMapper]]:
    """Yield the candidate passes applicable to this image, cheapest first."""
    yield ("binarized", *_binarized_pass(gray, invert=False))
    if float(gray.mean()) < _DARK_MEAN:
        yield ("inverted", *_binarized_pass(gray, invert=True))
    angle = _estimate_skew(gray)
    if angle is not None:
        yield ("deskewed", *_deskew_pass(gray, angle))


def _conf_mass(words: list[dict[str, Any]]) -> float:
    return sum(w["conf"] for w in words)


def _beats(current: list[dict[str, Any]],
           candidate: list[dict[str, Any]]) -> bool:
    """Decide whether a candidate pass replaces the current best.

    Against existing words the bar is simply more total confidence. Against *no* words it is the rescue bar: enough words at solid confidence that the result is believable as real recovered text rather than noise.
    """
    if not candidate:
        return False
    if current:
        return _conf_mass(candidate) > _conf_mass(current)
    return (len(candidate) >= _RESCUE_MIN_WORDS
            and _conf_mass(candidate) / len(candidate) >= _RESCUE_MIN_CONF)


def run(ctx: ImageContext) -> dict[str, Any]:
    if pytesseract is None:
        raise ModuleUnavailable("pytesseract is not installed (pip install pytesseract)")

    try:
        words = _extract_words(ctx.pil)
    except (pytesseract.TesseractNotFoundError, EnvironmentError) as exc:
        raise ModuleUnavailable(f"tesseract binary not available: {exc}") from exc

    used_pass = "original"
    # Candidate passes run when the first pass is shaky *or* empty. Empty is
    # allowed because tilted or inverted text often yields zero words rather
    # than low-confidence words — but then the rescue bar in _beats applies,
    # so text-free images stay honestly text-free.
    if not words or (_conf_mass(words) / len(words)) < _LOW_CONF:
        gray = _to_gray(ctx.pil)
        for name, image, mapper in _candidates(gray):
            try:
                alt = _extract_words(image)
            except Exception:  # pragma: no cover - candidates are best-effort
                continue
            alt = _map_words(alt, mapper)
            if _beats(words, alt):
                words, used_pass = alt, name

    if not words:
        return {"text": "", "lines": [], "paragraphs": [], "line_boxes": [],
                "word_boxes": [], "word_count": 0, "confidence": None,
                "position": None, "size": None, "pass": used_pass}

    line_records = _order_lines(words)
    line_texts = [r["text"] for r in line_records]
    paragraphs = _paragraphs(line_records)
    avg_conf = round(_conf_mass(words) / len(words), 1)

    # Word boxes are already mapped into ctx.pil space (the original image),
    # so normalise against the original dimensions — ctx.rgb may be a
    # downscaled working copy.
    img_w, img_h = ctx.pil.size

    def _rel(value: float, extent: int) -> float:
        return round(value / max(extent, 1), 3)

    line_boxes = [
        {"text": r["text"],
         "x0": _rel(r["left"], img_w), "y0": _rel(r["top"], img_h),
         "x1": _rel(r["right"], img_w), "y1": _rel(r["bottom"], img_h)}
        for r in line_records
    ]
    word_boxes = [
        {"text": w["text"],
         "cx": _rel(w["left"] + w["width"] / 2, img_w),
         "cy": _rel(w["top"] + w["height"] / 2, img_h)}
        for w in words[:80]
    ]

    # Locate and size the largest text element as a representative anchor.
    biggest = max(words, key=lambda w: w["height"])
    cx = biggest["left"] + biggest["width"] / 2
    cy = biggest["top"] + biggest["height"] / 2
    position = region_name(cx, cy, img_w, img_h)
    size = _size_label(biggest["height"], img_h)

    return {
        "text": " ".join(line_texts),
        "lines": line_texts,
        "paragraphs": paragraphs,
        "line_boxes": line_boxes,
        "word_boxes": word_boxes,
        "word_count": len(words),
        "confidence": avg_conf,
        "position": position,
        "size": size,
        "pass": used_pass,
    }


def render(data: dict[str, Any]) -> list[str]:
    if data["word_count"] == 0:
        return ["text: (none detected)"]
    reliability = "reliable" if (data["confidence"] or 0) >= 75 else "uncertain"
    # Lines join with " / ", paragraph breaks with " // " — one string, but the
    # document's structure survives for the model to read.
    paragraphs = data.get("paragraphs") or [data.get("lines") or [data["text"]]]
    text_repr = " // ".join(" / ".join(para) for para in paragraphs)
    lines = [
        f'text: "{text_repr}"',
        f"confidence: {data['confidence']}% ({reliability})",
        f"position: {data['position']}",
        f"size: {data['size']}",
    ]
    if data.get("pass") not in (None, "original", "binarized"):
        # Worth a token: the model learns the text was recovered from an
        # inverted or tilted image, which explains residual oddities.
        lines.append(f"recovered_via: {data['pass']} pass")
    return lines
