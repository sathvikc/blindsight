"""Region segmentation: describe the image as coloured regions plus relations.

This is the generic, token-cheap replacement for rasterising an image into
ASCII art. Character grids fail for language models twice over — the token
count scales with pixel count, and BPE tokenisation destroys the 2D alignment
the picture depends on. So instead of shipping pixels as characters, this
module segments the image classically (colour quantisation + connected
components) and ships *symbolic geometry*: each coherent region's colour name,
area share, position, elongation and texture, plus cross-region relations the
model can reason over in plain text:

- **bands** — full-width regions stacked vertically ("sky blue 0-38%, green
  38-100%" reads as an outdoor scene without any scene classifier);
- **baseline groups** — elements sharing a bottom edge, reported left to right
  with their heights ("4 tall elements share a baseline; heights 22%, 37%,
  29%, 51%" answers *which bar is tallest* with no chart-specific parser).

The interpretation is deliberately left to the language model; this module
only measures.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image

from ..colornames import nearest_name, to_hex
from ..context import ImageContext, ModuleUnavailable
from ..geometry import region_name

NAME = "regions"
TITLE = "Regions"

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

_MAX_SIDE = 256          # segmentation resolution; geometry is reported as fractions
_PALETTE = 10            # colour quantisation bins
_MIN_AREA_FRAC = 0.008   # ignore regions below 0.8% of the image
_MAX_REGIONS = 10
_BAND_MIN_WIDTH = 0.9    # a region this wide (relative) counts as a band
_BASELINE_TOL = 0.03     # bottom edges within 3% of image height align
_SMOOTH_STD = 14.0       # grayscale std below this reads as "smooth"


def _segment(pil: Image.Image) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Quantise a downscaled copy and return (labels, small_rgb, small_gray)."""
    small = pil.convert("RGB")
    small.thumbnail((_MAX_SIDE, _MAX_SIDE), Image.LANCZOS)
    quantized = small.quantize(colors=_PALETTE, method=Image.MEDIANCUT)
    labels = np.asarray(quantized, dtype=np.int32)
    rgb = np.asarray(small, dtype=np.uint8)
    gray = np.dot(rgb[..., :3], [0.299, 0.587, 0.114]).astype(np.uint8)
    return labels, rgb, gray


def _components(labels: np.ndarray, rgb: np.ndarray,
                gray: np.ndarray) -> list[dict[str, Any]]:
    """Connected components per colour bin, described in relative coordinates."""
    h, w = labels.shape
    image_area = float(h * w)
    kernel = np.ones((3, 3), np.uint8)

    regions: list[dict[str, Any]] = []
    for index in np.unique(labels):
        mask = (labels == index).astype(np.uint8)
        # Drop anti-aliasing speckle so components reflect real regions.
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        count, comp_labels, stats, centroids = cv2.connectedComponentsWithStats(mask)
        for comp in range(1, count):
            x, y, bw, bh, area = (int(v) for v in stats[comp])
            if area / image_area < _MIN_AREA_FRAC:
                continue
            comp_mask = comp_labels == comp
            mean_rgb = tuple(int(v) for v in rgb[comp_mask].mean(axis=0))
            cx, cy = centroids[comp]
            touches = sum((x == 0, y == 0, x + bw >= w, y + bh >= h))
            regions.append({
                "name": nearest_name(mean_rgb),
                "hex": to_hex(mean_rgb),
                "area_frac": round(area / image_area, 3),
                "bbox": [round(x / w, 3), round(y / h, 3),
                         round((x + bw) / w, 3), round((y + bh) / h, 3)],
                "position": region_name(cx, cy, w, h),
                "texture": ("smooth" if float(gray[comp_mask].std()) < _SMOOTH_STD
                            else "textured"),
                "background": touches == 4 and area / image_area >= 0.3,
            })

    regions.sort(key=lambda r: r["area_frac"], reverse=True)
    return regions[:_MAX_REGIONS]


def _aspect(bbox: list[float]) -> str | None:
    bw = max(bbox[2] - bbox[0], 1e-6)
    bh = max(bbox[3] - bbox[1], 1e-6)
    if bw >= 0.9 and bh >= 0.9:
        return "full-frame"
    ratio = bw / bh
    if ratio > 1.8:
        return "wide"
    if ratio < 0.55:
        return "tall"
    return None


def _bands(regions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]],
                                                   list[dict[str, Any]]]:
    """Vertical composition: full-width bands plus repeated-row stacks.

    Returns ``(bands, stacks)``. A band that vertically contains two or more
    other bands is a page/canvas backdrop, not a compositional layer, and is
    dropped. Three or more same-coloured bands of similar height collapse into
    a single "stack" — the signature of list rows in a UI — so the output says
    "5 white rows" instead of repeating five near-identical lines.
    """
    bands = [
        {"name": r["name"], "top": r["bbox"][1], "bottom": r["bbox"][3]}
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

    stacks: list[dict[str, Any]] = []
    by_name: dict[str, list[dict[str, Any]]] = {}
    for band in bands:
        by_name.setdefault(band["name"], []).append(band)
    stacked: list[dict[str, Any]] = []
    for name, group in by_name.items():
        # Cluster same-named bands by height so true repeated rows stack even
        # when thin background strips between them share the colour name.
        group.sort(key=lambda b: b["bottom"] - b["top"])
        clusters: list[list[dict[str, Any]]] = []
        for band in group:
            height = band["bottom"] - band["top"]
            if clusters and height <= 1.8 * max(
                    clusters[-1][0]["bottom"] - clusters[-1][0]["top"], 1e-6):
                clusters[-1].append(band)
            else:
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
            stacked.extend(cluster)
    bands = [b for b in bands if b not in stacked]

    if len(bands) < 2 and not stacks:
        return [], []
    return bands, stacks


def _baseline_groups(regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Groups of 3+ upright, non-background elements whose bottom edges align.

    Elements must be at least as tall as they are wide — that keeps real
    bar-like structures and rejects coincidental alignments of wide blobs
    (clouds, ground patches) whose bounding boxes merely end near the same row.
    """
    candidates = [
        r for r in regions
        if not r["background"]
        and (r["bbox"][2] - r["bbox"][0]) < _BAND_MIN_WIDTH
        and (r["bbox"][3] - r["bbox"][1]) >= (r["bbox"][2] - r["bbox"][0]) * 0.8
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
        # A meaningful baseline (chart axis, shelf, ground line) sits in the
        # lower half; alignments higher up are coincidence, not structure.
        if sum(r["bbox"][3] for r in group) / len(group) < 0.5:
            continue
        group.sort(key=lambda r: (r["bbox"][0] + r["bbox"][2]) / 2)
        result.append({
            "baseline": round(sum(r["bbox"][3] for r in group) / len(group), 3),
            "elements": [
                {"name": r["name"],
                 "height_frac": round(r["bbox"][3] - r["bbox"][1], 3)}
                for r in group
            ],
        })
    return result


def run(ctx: ImageContext) -> dict[str, Any]:
    if cv2 is None:
        raise ModuleUnavailable("opencv-python is not installed")

    labels, rgb, gray = _segment(ctx.pil)
    regions = _components(labels, rgb, gray)
    bands, stacks = _bands(regions)
    return {
        "count": len(regions),
        "regions": regions,
        "bands": bands,
        "stacks": stacks,
        "baseline_groups": _baseline_groups(regions),
    }


def _pct(frac: float) -> str:
    return f"{round(frac * 100)}%"


def render(data: dict[str, Any]) -> list[str]:
    if data["count"] == 0:
        return ["none"]

    lines: list[str] = []
    for r in data["regions"]:
        parts = [f"{r['name']} {r['hex']}", _pct(r["area_frac"])]
        if r["background"]:
            parts.append("background")
        else:
            parts.append(r["position"])
            aspect = _aspect(r["bbox"])
            if aspect:
                parts.append(aspect)
        parts.append(r["texture"])
        lines.append("- " + ", ".join(parts))

    if data["bands"]:
        spans = ", ".join(
            f"{b['name']} ({_pct(b['top'])}-{_pct(b['bottom'])})"
            for b in data["bands"]
        )
        lines.append(f"bands top->bottom: {spans}")

    for stack in data.get("stacks") or []:
        lines.append(
            f"rows: {stack['count']} {stack['name']} full-width rows "
            f"stacked {_pct(stack['top'])}-{_pct(stack['bottom'])}"
        )

    for group in data["baseline_groups"]:
        heights = ", ".join(
            f"{e['name']} h={_pct(e['height_frac'])}" for e in group["elements"]
        )
        lines.append(
            f"baseline: {len(group['elements'])} elements aligned at "
            f"y={_pct(group['baseline'])} - left->right: {heights}"
        )

    return lines
