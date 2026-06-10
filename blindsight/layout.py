"""Cross-module layout linking: connect OCR text to the regions it sits in.

OCR and regions each report positions, but separately they leave the model to
*assume* the association — that a title belongs to the chart, that "Save" is
the label of the blue button, that "Q1" names the first bar. This pass makes
those associations measured instead of assumed. It is derived from two module
results rather than from pixels, so it runs in the orchestrator after the
modules, and only when both OCR and regions produced content. Coordinates on
both sides are already relative (fractions of the image), so linking is pure
geometry:

- each prominent text line is matched to the smallest region containing its
  centre ("'Save' inside blue region" / "'Quarterly Revenue' on white
  background");
- baseline elements (bars) get the OCR word sitting just below each of them
  as a label, turning "blue h=29%" plus a separate "Q1 Q2 Q3" into a measured
  "blue=Q1".
"""

from __future__ import annotations

from typing import Any

from .descriptor import ModuleResult

NAME = "layout"
TITLE = "Layout"

_MAX_LINKS = 8
_MAX_TEXT = 40
_LABEL_BELOW = 0.15  # a bar's label sits within 15% of image height below it


def _trunc(text: str) -> str:
    return text if len(text) <= _MAX_TEXT else text[:_MAX_TEXT - 1] + "…"


def _link_lines(line_boxes: list[dict[str, Any]],
                regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for line in line_boxes[:_MAX_LINKS]:
        cx = (line["x0"] + line["x1"]) / 2
        cy = (line["y0"] + line["y1"]) / 2
        containing = [
            r for r in regions
            if not r["background"]
            and r["bbox"][0] <= cx <= r["bbox"][2]
            and r["bbox"][1] <= cy <= r["bbox"][3]
        ]
        if not containing:
            # Text sitting only on the page background ("on white") adds
            # nothing beyond what OCR already says — skip it.
            continue
        # The smallest containing region is the most specific home for the
        # text (a button inside a card inside the page background).
        region = min(containing, key=lambda r: r["area_frac"])
        links.append({
            "text": _trunc(line["text"]),
            "region": region["name"],
            "position": region["position"],
        })
    return links


def _label_baseline(group: dict[str, Any],
                    word_boxes: list[dict[str, Any]]) -> list[str | None] | None:
    """Per-element labels: the OCR word directly below each aligned element."""
    baseline = group["baseline"]
    labels: list[str | None] = []
    for element in group["elements"]:
        below = [
            w for w in word_boxes
            if element["x0"] <= w["cx"] <= element["x1"]
            and baseline - 0.02 <= w["cy"] <= baseline + _LABEL_BELOW
        ]
        below.sort(key=lambda w: w["cy"])
        labels.append(_trunc(below[0]["text"]) if below else None)
    if sum(label is not None for label in labels) < 2:
        return None
    return labels


def build(results: list[ModuleResult]) -> ModuleResult | None:
    """Derive the layout section, or ``None`` when there is nothing to link."""
    by_name = {r.name: r for r in results if r.available}
    ocr = by_name.get("ocr")
    reg = by_name.get("regions")
    if ocr is None or reg is None:
        return None

    line_boxes = ocr.data.get("line_boxes") or []
    regions = reg.data.get("regions") or []
    if not line_boxes or not regions:
        return None

    links = _link_lines(line_boxes, regions)

    labeled_groups: list[dict[str, Any]] = []
    word_boxes = ocr.data.get("word_boxes") or []
    for group in reg.data.get("baseline_groups") or []:
        labels = _label_baseline(group, word_boxes)
        if labels is None:
            continue
        labeled_groups.append({
            "labels": [
                {"name": e["name"], "label": label}
                for e, label in zip(group["elements"], labels)
            ],
        })

    if not links and not labeled_groups:
        return None

    return ModuleResult(
        name=NAME,
        title=TITLE,
        available=True,
        data={"links": links, "baseline_labels": labeled_groups},
        render=render,
    )


def render(data: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for link in data["links"]:
        lines.append(
            f'"{link["text"]}" inside {link["region"]} region ({link["position"]})'
        )
    for group in data["baseline_labels"]:
        pairs = ", ".join(
            f"{entry['name']}={entry['label'] or '?'}" for entry in group["labels"]
        )
        lines.append(f"baseline labels left->right: {pairs}")
    return lines
