"""Tests for the regions module: segmentation, bands, stacks, baselines.

Images are synthesised in-memory so the suite needs no asset files. Each test
targets one relation the module promises: baseline groups recover bar heights
in left-to-right order, bands recover vertical scene composition, and stacks
collapse repeated UI rows.
"""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from blindsight import extract


@pytest.fixture
def bar_chart_image(tmp_path):
    """Four solid bars of different heights sharing a baseline on white."""
    img = Image.new("RGB", (400, 300), "white")
    draw = ImageDraw.Draw(img)
    baseline = 260
    bars = [  # (x0, height, colour) left to right
        (40, 80, (31, 119, 180)),    # blue, shortest
        (130, 160, (255, 127, 14)),  # orange, tallest
        (220, 120, (44, 160, 44)),   # green
        (310, 140, (214, 39, 40)),   # red
    ]
    for x0, height, colour in bars:
        draw.rectangle([x0, baseline - height, x0 + 60, baseline], fill=colour)
    path = tmp_path / "bars.png"
    img.save(path)
    return str(path)


@pytest.fixture
def banded_image(tmp_path):
    """Sky-over-ground composition: blue top 40%, green bottom 60%."""
    img = Image.new("RGB", (400, 300), (100, 180, 235))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 120, 400, 300], fill=(30, 150, 60))
    path = tmp_path / "bands.png"
    img.save(path)
    return str(path)


@pytest.fixture
def rows_image(tmp_path):
    """A UI-like layout: blue header plus four identical white list rows."""
    img = Image.new("RGB", (400, 500), (230, 232, 236))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 400, 70], fill=(32, 98, 231))
    for i in range(4):
        top = 100 + i * 95
        draw.rectangle([0, top, 400, top + 70], fill="white")
    path = tmp_path / "rows.png"
    img.save(path)
    return str(path)


def test_baseline_group_recovers_bar_order_and_heights(bar_chart_image):
    data = extract(bar_chart_image, modules=["regions"]).get("regions").data
    assert data["baseline_groups"], "expected a baseline group for the bars"
    group = data["baseline_groups"][0]
    elements = group["elements"]
    assert len(elements) == 4

    heights = [e["height_frac"] for e in elements]
    # Drawn heights are 80, 160, 120, 140 px on a 300 px canvas; the tallest
    # must be second and the shortest first, and proportions roughly held.
    assert max(heights) == heights[1]
    assert min(heights) == heights[0]
    assert heights[1] == pytest.approx(160 / 300, abs=0.05)
    assert heights[0] == pytest.approx(80 / 300, abs=0.05)


def test_bands_report_vertical_composition(banded_image):
    data = extract(banded_image, modules=["regions"]).get("regions").data
    bands = data["bands"]
    assert len(bands) >= 2
    assert bands[0]["top"] < bands[1]["top"]
    names = [b["name"] for b in bands]
    assert any("blue" in n for n in names)
    assert any("green" in n for n in names)


def test_repeated_rows_collapse_into_stack(rows_image):
    data = extract(rows_image, modules=["regions"]).get("regions").data
    stacks = data["stacks"]
    assert stacks, "expected the four white rows to collapse into a stack"
    assert stacks[0]["name"] == "white"
    assert stacks[0]["count"] == 4


@pytest.fixture
def hbar_image(tmp_path):
    """Horizontal bars of different widths sharing a left edge."""
    img = Image.new("RGB", (400, 300), "white")
    draw = ImageDraw.Draw(img)
    bars = [  # (width, colour) top to bottom
        (280, (31, 119, 180)),
        (180, (255, 127, 14)),
        (220, (44, 160, 44)),
        (100, (214, 39, 40)),
    ]
    for i, (width, colour) in enumerate(bars):
        y = 40 + i * 60
        draw.rectangle([60, y, 60 + width, y + 40], fill=colour)
    path = tmp_path / "hbar.png"
    img.save(path)
    return str(path)


@pytest.fixture
def gradient_image(tmp_path):
    """A smooth vertical gradient from warm orange to dark blue."""
    img = Image.new("RGB", (400, 300))
    draw = ImageDraw.Draw(img)
    for y in range(300):
        t = y / 300
        draw.line(
            [(0, y), (400, y)],
            fill=(int(250 - 180 * t), int(160 - 100 * t), int(90 + 60 * t)),
        )
    path = tmp_path / "gradient.png"
    img.save(path)
    return str(path)


def test_left_edge_group_recovers_horizontal_bar_widths(hbar_image):
    data = extract(hbar_image, modules=["regions"]).get("regions").data
    assert data["left_edge_groups"], "expected a left-aligned group for the bars"
    elements = data["left_edge_groups"][0]["elements"]
    assert len(elements) == 4

    widths = [e["width_frac"] for e in elements]
    # Drawn widths are 280, 180, 220, 100 px on a 400 px canvas.
    assert max(widths) == widths[0]
    assert min(widths) == widths[3]
    assert widths[0] == pytest.approx(280 / 400, abs=0.05)


def test_gradient_is_one_gradient_not_rows(gradient_image):
    data = extract(gradient_image, modules=["regions"]).get("regions").data
    assert data["gradients"], "expected the gradient to be detected"
    assert data["stacks"] == [], "a gradient must not masquerade as UI rows"
    grad = data["gradients"][0]
    assert grad["top"] == pytest.approx(0.0, abs=0.05)
    assert grad["bottom"] == pytest.approx(1.0, abs=0.05)


def test_plain_background_yields_no_relations(tmp_path):
    img = Image.new("RGB", (300, 300), "white")
    path = tmp_path / "plain.png"
    img.save(path)
    data = extract(str(path), modules=["regions"]).get("regions").data
    assert data["baseline_groups"] == []
    assert data["bands"] == []
    assert data["stacks"] == []
    assert data["gradients"] == []
    assert data["left_edge_groups"] == []


def test_render_mentions_baseline(bar_chart_image):
    text = extract(bar_chart_image, modules=["regions"]).to_text()
    assert "[Regions]" in text
    assert "baseline:" in text
    assert "left->right" in text
