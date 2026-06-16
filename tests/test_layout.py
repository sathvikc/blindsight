"""Tests for cross-module layout linking (OCR text <-> regions)."""

from __future__ import annotations

from blindsight import layout
from blindsight.descriptor import ModuleResult


def _ocr_result(line_boxes, word_boxes=()):
    return ModuleResult(
        name="ocr", title="OCR", available=True,
        data={"line_boxes": list(line_boxes), "word_boxes": list(word_boxes)},
    )


def _regions_result(regions, baseline_groups=()):
    return ModuleResult(
        name="regions", title="Regions", available=True,
        data={"regions": list(regions),
              "baseline_groups": list(baseline_groups)},
    )


_BLUE_HEADER = {
    "name": "blue", "hex": "#2062E7", "area_frac": 0.12,
    "bbox": [0.0, 0.0, 1.0, 0.15], "position": "top-center",
    "texture": "smooth", "background": False,
}
_WHITE_BG = {
    "name": "white", "hex": "#FFFFFF", "area_frac": 0.7,
    "bbox": [0.0, 0.0, 1.0, 1.0], "position": "center",
    "texture": "smooth", "background": True,
}


def test_text_links_to_containing_region():
    ocr = _ocr_result([
        {"text": "Settings", "x0": 0.3, "y0": 0.04, "x1": 0.7, "y1": 0.10},
        {"text": "stray", "x0": 0.3, "y0": 0.5, "x1": 0.5, "y1": 0.55},
    ])
    reg = _regions_result([_WHITE_BG, _BLUE_HEADER])

    result = layout.build([ocr, reg])
    assert result is not None
    links = result.data["links"]
    # "Settings" lands in the blue header; "stray" sits only on the
    # background and is skipped as uninformative.
    assert len(links) == 1
    assert links[0]["text"] == "Settings"
    assert links[0]["region"] == "blue"


def test_smallest_containing_region_wins():
    button = {
        "name": "green", "hex": "#2C9F2C", "area_frac": 0.02,
        "bbox": [0.35, 0.02, 0.65, 0.12], "position": "top-center",
        "texture": "smooth", "background": False,
    }
    ocr = _ocr_result([
        {"text": "OK", "x0": 0.45, "y0": 0.05, "x1": 0.55, "y1": 0.09},
    ])
    reg = _regions_result([_WHITE_BG, _BLUE_HEADER, button])

    links = layout.build([ocr, reg]).data["links"]
    assert links[0]["region"] == "green"


def test_baseline_elements_get_labels_from_words_below():
    group = {
        "baseline": 0.85,
        "elements": [
            {"name": "blue", "height_frac": 0.3, "x0": 0.10, "x1": 0.25},
            {"name": "red", "height_frac": 0.5, "x0": 0.40, "x1": 0.55},
            {"name": "green", "height_frac": 0.4, "x0": 0.70, "x1": 0.85},
        ],
    }
    bars = [
        {"name": n, "hex": "#000000", "area_frac": 0.05,
         "bbox": [0.1, 0.5, 0.2, 0.85], "position": "bottom-center",
         "texture": "smooth", "background": False}
        for n in ("blue", "red", "green")
    ]
    ocr = _ocr_result(
        [{"text": "Chart", "x0": 0.3, "y0": 0.01, "x1": 0.7, "y1": 0.05}],
        word_boxes=[
            {"text": "Q1", "cx": 0.17, "cy": 0.92},
            {"text": "Q2", "cx": 0.47, "cy": 0.92},
            # No label under the green bar — must come back as None.
        ],
    )
    reg = _regions_result([_WHITE_BG, *bars], baseline_groups=[group])

    result = layout.build([ocr, reg])
    labels = result.data["baseline_labels"][0]["labels"]
    assert [entry["label"] for entry in labels] == ["Q1", "Q2", None]


def test_no_section_when_nothing_links():
    ocr = _ocr_result([
        {"text": "hello", "x0": 0.1, "y0": 0.1, "x1": 0.3, "y1": 0.15},
    ])
    reg = _regions_result([_WHITE_BG])
    assert layout.build([ocr, reg]) is None


def test_no_section_without_both_modules():
    ocr = _ocr_result([
        {"text": "hello", "x0": 0.1, "y0": 0.1, "x1": 0.3, "y1": 0.15},
    ])
    assert layout.build([ocr]) is None
