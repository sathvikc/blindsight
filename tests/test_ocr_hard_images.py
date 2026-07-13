"""OCR candidate passes on hard images: inverted, tilted, and text-free.

These tests synthesize the specific failure modes the candidate passes exist for and run the real module end to end (they skip cleanly when Tesseract is missing, like the OCR module itself degrades). The text-free cases are the most important ones: the rescue bar must keep honest negatives honest even though extra passes now run on empty first results.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from blindsight.context import load_context
from blindsight.modules import ocr


def _tesseract_available() -> bool:
    if ocr.pytesseract is None:
        return False
    try:
        ocr.pytesseract.get_tesseract_version()
    except Exception:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _tesseract_available(), reason="tesseract not installed")


def _font(size: int = 28):
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _text_image(lines: list[str], fg: int, bg: int,
                size: tuple[int, int] = (640, 320)) -> Image.Image:
    img = Image.new("L", size, bg)
    draw = ImageDraw.Draw(img)
    y = 40
    for line in lines:
        draw.text((40, y), line, fill=fg, font=_font())
        y += 48
    return img


def _run(img: Image.Image, tmp_path) -> dict:
    path = tmp_path / "img.png"
    img.save(path)
    return ocr.run(load_context(str(path)))


def test_light_on_dark_text_is_recovered(tmp_path):
    img = _text_image(["ERROR: DISK FULL", "CODE 0x8007000E"], fg=235, bg=20)
    data = _run(img, tmp_path)
    assert "DISK" in data["text"]
    assert "0x8007000E" in data["text"]


def test_tilted_document_is_recovered_by_deskew(tmp_path):
    base = _text_image(
        ["INVOICE NUMBER 42-A", "TOTAL DUE 1,234.56", "PAY BY 2026-08-01"],
        fg=0, bg=255)
    tilted = base.rotate(8, expand=True, fillcolor=255,
                         resample=Image.BICUBIC)
    data = _run(tilted, tmp_path)
    assert "INVOICE" in data["text"]
    assert "1,234.56" in data["text"]
    assert data["pass"] == "deskewed"


def test_tilted_the_other_way_is_also_recovered(tmp_path):
    base = _text_image(
        ["INVOICE NUMBER 42-A", "TOTAL DUE 1,234.56", "PAY BY 2026-08-01"],
        fg=0, bg=255)
    tilted = base.rotate(-8, expand=True, fillcolor=255,
                         resample=Image.BICUBIC)
    data = _run(tilted, tmp_path)
    assert "INVOICE" in data["text"]


def test_deskewed_boxes_land_back_in_original_space(tmp_path):
    base = _text_image(["ANCHOR TEXT HERE"], fg=0, bg=255, size=(640, 200))
    tilted = base.rotate(10, expand=True, fillcolor=255,
                         resample=Image.BICUBIC)
    data = _run(tilted, tmp_path)
    for box in data["line_boxes"]:
        assert 0.0 <= box["x0"] <= box["x1"] <= 1.0
        assert 0.0 <= box["y0"] <= box["y1"] <= 1.0


def test_flat_image_stays_text_free(tmp_path):
    img = Image.new("L", (400, 300), 128)
    data = _run(img, tmp_path)
    assert data["word_count"] == 0
    assert data["text"] == ""


def test_noise_image_stays_text_free(tmp_path):
    rng = np.random.default_rng(7)
    noise = rng.integers(0, 256, size=(300, 400), dtype=np.uint8)
    data = _run(Image.fromarray(noise), tmp_path)
    # The rescue bar: scattered low-confidence fragments must not be promoted
    # to "text" just because extra passes ran.
    assert data["word_count"] == 0 or data["confidence"] >= 60


def test_dark_noise_image_stays_text_free(tmp_path):
    # Dark noise additionally triggers the inverted candidate pass.
    rng = np.random.default_rng(11)
    noise = rng.integers(0, 90, size=(300, 400), dtype=np.uint8)
    data = _run(Image.fromarray(noise), tmp_path)
    assert data["word_count"] == 0 or data["confidence"] >= 60


def test_paragraph_structure_is_reported(tmp_path):
    img = Image.new("L", (640, 480), 255)
    draw = ImageDraw.Draw(img)
    draw.text((40, 40), "FIRST PARAGRAPH LINE", fill=0, font=_font())
    draw.text((40, 88), "SECOND LINE SAME BLOCK", fill=0, font=_font())
    # A wide vertical gap makes Tesseract open a new block/paragraph.
    draw.text((40, 380), "FOOTER PARAGRAPH", fill=0, font=_font())
    data = _run(img, tmp_path)
    assert len(data["paragraphs"]) >= 2
    flat = [line for para in data["paragraphs"] for line in para]
    assert flat == data["lines"]
