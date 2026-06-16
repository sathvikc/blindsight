"""Property-based tests: randomly generated images with known ground truth.

The showcase benchmark is a handful of hand-picked images; these tests guard
against overfitting to it. Every test draws a random instance of a *family*
of images (bar charts, horizontal bars, gradients, UI row layouts, blanks,
noise) from a seeded RNG and asserts the properties the regions module
promises — element counts, orderings, and proportions recovered within
tolerance, and *no* relations invented where none exist. New seeds are new
images, so a passing run is evidence about the family, not about any one
picture.
"""

from __future__ import annotations

import random

import numpy as np
import pytest
from PIL import Image, ImageDraw

from blindsight import extract

SEEDS = range(8)

# Well-separated colours so quantisation never merges two elements.
_COLOURS = [
    (31, 119, 180),    # blue
    (255, 127, 14),    # orange
    (44, 160, 44),     # green
    (214, 39, 40),     # red
    (148, 103, 189),   # purple
    (140, 86, 75),     # brown
]


def _regions_data(path: str) -> dict:
    return extract(path, modules=["regions"]).get("regions").data


def _ranks(values: list[float]) -> list[int]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0] * len(values)
    for rank, index in enumerate(order):
        ranks[index] = rank
    return ranks


@pytest.mark.parametrize("seed", SEEDS)
def test_random_vertical_bars_recover_order_and_proportions(seed, tmp_path):
    rnd = random.Random(seed)
    n = rnd.randint(3, 5)
    # Distinct heights at least 30 px apart so orderings are unambiguous.
    heights = rnd.sample(range(60, 211, 30), n)
    colours = rnd.sample(_COLOURS, n)

    width, height, baseline = 480, 320, 280
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    slot = width // (n + 1)
    for i, (h, colour) in enumerate(zip(heights, colours)):
        x = slot * (i + 1) - 25
        draw.rectangle([x, baseline - h, x + 50, baseline], fill=colour)
    path = tmp_path / f"vbars_{seed}.png"
    img.save(path)

    data = _regions_data(str(path))
    assert data["baseline_groups"], f"seed {seed}: no baseline group found"
    elements = data["baseline_groups"][0]["elements"]
    assert len(elements) == n, f"seed {seed}: {len(elements)} of {n} bars"

    measured = [e["height_frac"] for e in elements]
    expected = [h / height for h in heights]
    assert _ranks(measured) == _ranks(expected), f"seed {seed}: order broken"
    for m, e in zip(measured, expected):
        assert m == pytest.approx(e, abs=0.06), f"seed {seed}: proportion off"


@pytest.mark.parametrize("seed", SEEDS)
def test_random_horizontal_bars_recover_order_and_proportions(seed, tmp_path):
    rnd = random.Random(seed)
    n = rnd.randint(3, 4)
    widths = rnd.sample(range(100, 301, 40), n)
    colours = rnd.sample(_COLOURS, n)

    canvas_w, canvas_h, left = 480, 320, 60
    img = Image.new("RGB", (canvas_w, canvas_h), "white")
    draw = ImageDraw.Draw(img)
    for i, (w, colour) in enumerate(zip(widths, colours)):
        y = 30 + i * 70
        draw.rectangle([left, y, left + w, y + 45], fill=colour)
    path = tmp_path / f"hbars_{seed}.png"
    img.save(path)

    data = _regions_data(str(path))
    assert data["left_edge_groups"], f"seed {seed}: no left-edge group found"
    elements = data["left_edge_groups"][0]["elements"]
    assert len(elements) == n, f"seed {seed}: {len(elements)} of {n} bars"

    measured = [e["width_frac"] for e in elements]
    expected = [w / canvas_w for w in widths]
    assert _ranks(measured) == _ranks(expected), f"seed {seed}: order broken"
    for m, e in zip(measured, expected):
        assert m == pytest.approx(e, abs=0.06), f"seed {seed}: proportion off"


@pytest.mark.parametrize("seed", SEEDS)
def test_random_gradient_is_gradient_not_rows(seed, tmp_path):
    rnd = random.Random(seed)
    while True:  # endpoints far enough apart to actually be a gradient
        c0, c1 = rnd.sample(_COLOURS, 2)
        if sum((a - b) ** 2 for a, b in zip(c0, c1)) ** 0.5 >= 120:
            break

    img = Image.new("RGB", (400, 300))
    draw = ImageDraw.Draw(img)
    for y in range(300):
        t = y / 299
        draw.line(
            [(0, y), (400, y)],
            fill=tuple(round(a + (b - a) * t) for a, b in zip(c0, c1)),
        )
    path = tmp_path / f"grad_{seed}.png"
    img.save(path)

    data = _regions_data(str(path))
    assert data["gradients"], f"seed {seed}: gradient not detected"
    assert data["stacks"] == [], f"seed {seed}: gradient mistaken for rows"
    assert data["baseline_groups"] == [], f"seed {seed}: phantom baseline"


@pytest.mark.parametrize("seed", SEEDS)
def test_random_ui_rows_collapse_into_stack(seed, tmp_path):
    rnd = random.Random(seed)
    n = rnd.randint(3, 6)
    row_h = rnd.randint(50, 70)
    gap = rnd.randint(20, 35)

    height = 80 + 30 + n * (row_h + gap) + 30
    img = Image.new("RGB", (400, height), (228, 230, 234))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 400, 80], fill=rnd.choice(_COLOURS))
    for i in range(n):
        top = 80 + 30 + i * (row_h + gap)
        draw.rectangle([0, top, 400, top + row_h], fill="white")
    path = tmp_path / f"rows_{seed}.png"
    img.save(path)

    data = _regions_data(str(path))
    counts = [s["count"] for s in data["stacks"] if s["name"] == "white"]
    assert n in counts, f"seed {seed}: expected a stack of {n} white rows"
    assert data["gradients"] == [], f"seed {seed}: rows mistaken for gradient"


@pytest.mark.parametrize("seed", SEEDS)
def test_random_featureless_images_invent_no_structure(seed, tmp_path):
    rnd = random.Random(seed)
    if seed % 2 == 0:
        shade = rnd.randint(0, 255)
        arr = np.full((300, 400, 3), shade, dtype=np.uint8)
    else:
        arr = (np.random.default_rng(seed).random((300, 400, 3)) * 255
               ).astype(np.uint8)
    path = tmp_path / f"flat_{seed}.png"
    Image.fromarray(arr).save(path)

    data = _regions_data(str(path))
    assert data["baseline_groups"] == [], f"seed {seed}: phantom baseline"
    assert data["left_edge_groups"] == [], f"seed {seed}: phantom left edge"
    assert data["stacks"] == [], f"seed {seed}: phantom rows"
    assert data["gradients"] == [], f"seed {seed}: phantom gradient"
