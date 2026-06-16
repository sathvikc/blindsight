"""Tests for the extraction pipeline.

Images are synthesised in-memory so the suite needs no asset files and no
network. OCR/Tesseract is optional, so tests assert on availability handling
rather than requiring the binary.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageDraw

from blindsight import extract
from blindsight.geometry import region_name, size_bucket


@pytest.fixture
def shapes_image(tmp_path):
    """A white canvas with a black rectangle and a solid red circle."""
    img = Image.new("RGB", (400, 300), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, 180, 160], outline="black", width=4)
    draw.ellipse([260, 180, 360, 280], fill="red")
    path = tmp_path / "shapes.png"
    img.save(path)
    return str(path)


@pytest.fixture
def gray_image(tmp_path):
    arr = np.full((100, 100, 3), 128, dtype=np.uint8)
    path = tmp_path / "gray.png"
    Image.fromarray(arr).save(path)
    return str(path)


def test_extract_reports_all_modules(shapes_image):
    descriptor = extract(shapes_image)
    names = {r.name for r in descriptor.results}
    assert names == {"stats", "ocr", "colors", "regions", "structure",
                     "shapes", "faces", "codes", "exif"}


def test_stats_resolution_matches_source(shapes_image):
    stats = extract(shapes_image).get("stats")
    assert stats.available
    assert stats.data["resolution"] == "400x300"
    assert stats.data["orientation"] == "landscape"


def test_grayscale_detection(gray_image, shapes_image):
    assert extract(gray_image).get("colors").data["grayscale"] is True
    assert extract(shapes_image).get("colors").data["grayscale"] is False


def test_shapes_detected(shapes_image):
    shapes = extract(shapes_image).get("shapes")
    assert shapes.available
    assert shapes.data["count"] >= 1


def test_text_output_is_block(shapes_image):
    text = extract(shapes_image).to_text()
    assert text.startswith("=== IMAGE DESCRIPTOR ===")
    assert "[Stats]" in text
    assert "[Colors]" in text


def test_json_output_structure(shapes_image):
    payload = extract(shapes_image).to_json()
    assert payload["width"] == 400
    assert "stats" in payload["modules"]
    assert payload["modules"]["stats"]["available"] is True


def test_module_subset_selection(shapes_image):
    descriptor = extract(shapes_image, modules=["stats", "colors"])
    assert {r.name for r in descriptor.results} == {"stats", "colors"}


def test_unavailable_module_does_not_crash(shapes_image, monkeypatch):
    # Force the colors module to raise; extraction must still complete.
    from blindsight.modules import colors

    monkeypatch.setattr(colors, "run", lambda ctx: (_ for _ in ()).throw(RuntimeError("boom")))
    result = extract(shapes_image).get("colors")
    assert result.available is False
    assert "boom" in result.note


@pytest.mark.parametrize("cx,cy,expected", [
    (10, 10, "top-left"),
    (50, 50, "center"),
    (95, 95, "bottom-right"),
    (50, 10, "top-center"),
])
def test_region_name(cx, cy, expected):
    assert region_name(cx, cy, 100, 100) == expected


def test_size_bucket():
    assert size_bucket(1, 1000) == "small"
    assert size_bucket(100, 1000) == "medium"
    assert size_bucket(500, 1000) == "large"
