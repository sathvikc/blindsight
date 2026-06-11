"""Cross-region relations: bands, gradients, row stacks, alignment groups.

Pure functions over the region dicts produced by ``modules/regions.py``
(``{"name", "hex", "area_frac", "bbox", "position", "texture",
"background"}``). Split out of the regions module so the segmentation code
and the relation heuristics can evolve separately.
"""

from __future__ import annotations

from typing import Any

_BAND_MIN_WIDTH = 0.9    # a region this wide (relative) counts as a band
_BASELINE_TOL = 0.03     # edges within 3% of the image extent align


def _band_rgb(band: dict[str, Any]) -> tuple[int, int, int]:
    value = band["hex"].lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _colour_dist(a: dict[str, Any], b: dict[str, Any]) -> float:
    return sum((x - y) ** 2 for x, y in zip(_band_rgb(a), _band_rgb(b))) ** 0.5


def bands_stacks_gradients(
    regions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Vertical composition: full-width bands, repeated-row stacks, gradients.

    Returns ``(bands, stacks, gradients)``. A band that vertically contains
    two or more other bands is a page/canvas backdrop, not a compositional
    layer, and is dropped. Contiguous colour-shifting runs become gradients
    (see :func:`merge_gradients`); same-coloured bands of similar height
    separated by gaps collapse into a "stack" — the signature of list rows in
    a UI — so the output says "5 white rows" instead of five near-identical
    lines.
    """
    bands = [
        {"name": r["name"], "hex": r["hex"],
         "top": r["bbox"][1], "bottom": r["bbox"][3]}
        for r in regions
        if (r["bbox"][2] - r["bbox"][0]) >= _BAND_MIN_WIDTH and not r["background"]
    ]
    bands.sort(key=lambda b: b["top"])

    def _contains(outer: dict[str, Any], inner: dict[str, Any]) -> bool:
        return (outer is not inner
                and outer["top"] <= inner["top"] + 0.01
                and outer["bottom"] >= inner["bottom"] - 0.01)

    bands = [
        b for b in bands
        if sum(_contains(b, other) for other in bands) < 2
    ]

    bands, gradients = merge_gradients(bands)

    stacks: list[dict[str, Any]] = []
    by_name: dict[str, list[dict[str, Any]]] = {}
    for band in bands:
        by_name.setdefault(band["name"], []).append(band)
    stacked_ids: set[int] = set()
    for name, group in by_name.items():
        group.sort(key=lambda b: b["bottom"] - b["top"])
        clusters: list[list[dict[str, Any]]] = []
        for band in group:
            height = band["bottom"] - band["top"]
            if clusters:
                anchor = clusters[-1][0]
                anchor_height = max(anchor["bottom"] - anchor["top"], 1e-6)
                if (height <= 1.8 * anchor_height
                        and _colour_dist(band, anchor) <= 30.0):
                    clusters[-1].append(band)
                    continue
            clusters.append([band])
        for cluster in clusters:
            if len(cluster) < 3:
                continue
            cluster.sort(key=lambda b: b["top"])
            stacks.append({
                "name": name,
                "count": len(cluster),
                "top": cluster[0]["top"],
                "bottom": cluster[-1]["bottom"],
            })
            stacked_ids.update(id(b) for b in cluster)
    # Filter by identity, not value: two distinct bands can compare equal.
    bands = [b for b in bands if id(b) not in stacked_ids]

    if len(bands) < 2 and not stacks and not gradients:
        return [], [], gradients
    return bands, stacks, gradients


def merge_gradients(
    bands: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Collapse runs of 3+ contiguous, colour-shifting bands into gradients.

    Quantisation slices a smooth vertical gradient (sunset sky, vignette)
    into stacked strips. Real UI rows are separated by background gaps;
    gradient strips touch and each strip's colour differs slightly from the
    next. Reporting the run as one gradient avoids describing a sky as
    "rows".
    """
    ordered = sorted(bands, key=lambda b: b["top"])

    runs: list[list[dict[str, Any]]] = []
    for band in ordered:
        if runs:
            gap = band["top"] - runs[-1][-1]["bottom"]
            if -0.05 <= gap <= 0.01:
                runs[-1].append(band)
                continue
        runs.append([band])

    gradients: list[dict[str, Any]] = []
    merged_ids: set[int] = set()
    for run in runs:
        if len(run) < 3:
            continue
        steps = [_colour_dist(run[i], run[i + 1]) for i in range(len(run) - 1)]
        end_to_end = _colour_dist(run[0], run[-1])
        if (min(steps) >= 8.0
                and end_to_end >= 0.5 * sum(steps)):
            gradients.append({
                "from": run[0]["name"],
                "to": run[-1]["name"],
                "top": run[0]["top"],
                "bottom": run[-1]["bottom"],
            })
            merged_ids.update(id(b) for b in run)
    # Filter by identity, not value: two distinct bands can compare equal.
    return [b for b in bands if id(b) not in merged_ids], gradients


def baseline_groups(regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Groups of 3+ upright, non-background elements whose bottom edges align.

    Elements must be at least as tall as they are wide — that keeps real
    bar-like structures and rejects coincidental alignments of wide blobs
    (clouds, ground patches) whose bounding boxes merely end near the same
    row.
    """
    candidates = [
        r for r in regions
        if not r["background"]
        and (r["bbox"][2] - r["bbox"][0]) < _BAND_MIN_WIDTH
        and (r["bbox"][3] - r["bbox"][1])
        >= (r["bbox"][2] - r["bbox"][0]) * 0.8
    ]
    candidates.sort(key=lambda r: r["bbox"][3])

    groups: list[list[dict[str, Any]]] = []
    for region in candidates:
        if groups and abs(region["bbox"][3] - groups[-1][-1]["bbox"][3]) <= _BASELINE_TOL:
            groups[-1].append(region)
        else:
            groups.append([region])

    result: list[dict[str, Any]] = []
    for group in groups:
        if len(group) < 3:
            continue
        if sum(r["bbox"][3] for r in group) / len(group) < 0.5:
            continue
        widths = [r["bbox"][2] - r["bbox"][0] for r in group]
        if max(widths) > 2.5 * max(min(widths), 1e-6):
            continue
        group.sort(key=lambda r: (r["bbox"][0] + r["bbox"][2]) / 2)
        result.append({
            "baseline": round(sum(r["bbox"][3] for r in group) / len(group), 3),
            "elements": [
                {"name": r["name"],
                 "height_frac": round(r["bbox"][3] - r["bbox"][1], 3),
                 "x0": r["bbox"][0], "x1": r["bbox"][2]}
                for r in group
            ],
        })
    return result


def left_edge_groups(regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Groups of 3+ flat, non-background elements whose left edges align.

    The horizontal twin of :func:`baseline_groups`: horizontal bar charts,
    lists and indented blocks share a left edge instead of a bottom edge.
    """
    candidates = [
        r for r in regions
        if not r["background"]
        and (r["bbox"][2] - r["bbox"][0]) < _BAND_MIN_WIDTH
        and (r["bbox"][2] - r["bbox"][0])
        >= (r["bbox"][3] - r["bbox"][1]) * 0.8
    ]
    candidates.sort(key=lambda r: r["bbox"][0])

    groups: list[list[dict[str, Any]]] = []
    for region in candidates:
        if groups and abs(region["bbox"][0] - groups[-1][-1]["bbox"][0]) <= _BASELINE_TOL:
            groups[-1].append(region)
        else:
            groups.append([region])

    result: list[dict[str, Any]] = []
    for group in groups:
        if len(group) < 3:
            continue
        if sum(r["bbox"][0] for r in group) / len(group) > 0.35:
            continue
        heights = [r["bbox"][3] - r["bbox"][1] for r in group]
        if max(heights) > 2.5 * max(min(heights), 1e-6):
            continue
        group.sort(key=lambda r: (r["bbox"][1] + r["bbox"][3]) / 2)
        result.append({
            "edge": round(sum(r["bbox"][0] for r in group) / len(group), 3),
            "elements": [
                {"name": r["name"],
                 "width_frac": round(r["bbox"][2] - r["bbox"][0], 3),
                 "y0": r["bbox"][1], "y1": r["bbox"][3]}
                for r in group
            ],
        })
    return result
