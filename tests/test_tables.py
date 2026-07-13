"""Tables module: ruled-grid reconstruction and its anti-hallucination gates.

The positive cases synthesize genuinely ruled tables and assert the grid and cell contents come back. The negative cases are the point of the module's gates: bar-chart gridlines, a lone rectangle, noise, and flat images must yield *no* table rather than an invented one.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from blindsight.context import load_context
from blindsight.modules import tables


def _tesseract_available() -> bool:
    if tables.pytesseract is None:
        return False
    try:
        tables.pytesseract.get_tesseract_version()
    except Exception:
        return False
    return True


def _font(size: int = 20):
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _ruled_table(cell_texts: list[list[str]],
                 cell_w: int = 150, cell_h: int = 56,
                 margin: int = 40) -> Image.Image:
    rows, cols = len(cell_texts), len(cell_texts[0])
    img = Image.new("L", (margin * 2 + cols * cell_w,
                          margin * 2 + rows * cell_h), 255)
    draw = ImageDraw.Draw(img)
    for r in range(rows + 1):
        y = margin + r * cell_h
        draw.line([(margin, y), (margin + cols * cell_w, y)], fill=0, width=2)
    for c in range(cols + 1):
        x = margin + c * cell_w
        draw.line([(x, margin), (x, margin + rows * cell_h)], fill=0, width=2)
    font = _font()
    for r, row in enumerate(cell_texts):
        for c, text in enumerate(row):
            draw.text((margin + c * cell_w + 12, margin + r * cell_h + 16),
                      text, fill=0, font=font)
    return img


def _run(img: Image.Image, tmp_path) -> dict:
    path = tmp_path / "img.png"
    img.save(path)
    return tables.run(load_context(str(path)))


def test_grid_geometry_is_recovered(tmp_path):
    img = _ruled_table([["A", "B", "C"], ["D", "E", "F"],
                        ["G", "H", "I"], ["J", "K", "L"]])
    data = _run(img, tmp_path)
    assert data["count"] == 1
    assert data["tables"][0]["rows"] == 4
    assert data["tables"][0]["cols"] == 3


@pytest.mark.skipif(not _tesseract_available(), reason="tesseract not installed")
def test_cell_contents_keep_row_column_association(tmp_path):
    img = _ruled_table([
        ["Item", "Qty", "Price"],
        ["Milk", "2", "90.00"],
        ["Eggs", "1", "120.00"],
    ])
    data = _run(img, tmp_path)
    assert data["count"] == 1
    cells = data["tables"][0]["cells"]
    assert cells[0] == ["Item", "Qty", "Price"]
    assert cells[1] == ["Milk", "2", "90.00"]
    assert cells[2] == ["Eggs", "1", "120.00"]


@pytest.mark.skipif(not _tesseract_available(), reason="tesseract not installed")
def test_render_produces_pipe_rows(tmp_path):
    img = _ruled_table([["Name", "Score"], ["Ada", "97"], ["Alan", "95"]])
    data = _run(img, tmp_path)
    body = tables.render(data)
    assert any("| Name | Score |" in line for line in body)
    assert any("| Ada | 97 |" in line for line in body)


def test_lone_rectangle_is_not_a_table(tmp_path):
    img = Image.new("L", (600, 400), 255)
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 80, 500, 320], outline=0, width=3)
    data = _run(img, tmp_path)
    assert data["count"] == 0


def test_chart_gridlines_alone_are_not_a_table(tmp_path):
    # Horizontal gridlines + one y-axis: parallel lines with almost no
    # crossings must not become a "table".
    img = Image.new("L", (600, 400), 255)
    draw = ImageDraw.Draw(img)
    for y in range(60, 380, 60):
        draw.line([(80, y), (560, y)], fill=180, width=1)
    draw.line([(80, 40), (80, 370)], fill=0, width=2)
    data = _run(img, tmp_path)
    assert data["count"] == 0


def test_flat_image_has_no_table(tmp_path):
    data = _run(Image.new("L", (400, 300), 200), tmp_path)
    assert data["count"] == 0


def test_noise_image_has_no_table(tmp_path):
    rng = np.random.default_rng(23)
    noise = rng.integers(0, 256, size=(300, 400), dtype=np.uint8)
    data = _run(Image.fromarray(noise), tmp_path)
    assert data["count"] == 0


def test_relative_bbox_is_normalized(tmp_path):
    img = _ruled_table([["A", "B"], ["C", "D"], ["E", "F"]])
    data = _run(img, tmp_path)
    assert data["count"] == 1
    bbox = data["tables"][0]["bbox"]
    assert 0.0 <= bbox[0] < bbox[2] <= 1.0
    assert 0.0 <= bbox[1] < bbox[3] <= 1.0
