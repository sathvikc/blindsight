"""Spatial relation engine — the 'where' layer.

Blindsight's detector modules each answer *what* is in an image (text, shapes,
faces) but emit their findings as separate flat lists. The questions they miss
are almost always *relational*: which value sits above which axis label, which
menu row lacks a toggle, which word is inside which button. Those answers live
in the geometry *between* detections, which no single module computes.

This module fuses heterogeneous detections into one typed spatial graph using
nothing but coordinate geometry — no machine learning, fully deterministic. A
node is any detected element; relations (`rows`, `columns`, `contains`) are
derived by rule. The output is meant to be *reasoned over* by a language model,
not visually perceived: it hands the model explicit relations rather than asking
it to recover them from a pixel grid.

A node is a dict with at least::

    {"kind": "text", "label": "Save", "box": (left, top, w, h)}  # box in [0, 1]

Coordinates are normalised to the unit square so nodes from different detectors
(which may run on differently scaled images) are directly comparable.
"""

from __future__ import annotations

from typing import Any

Node = dict[str, Any]


def _cx(n: Node) -> float:
    left, _top, w, _h = n["box"]
    return left + w / 2


def _cy(n: Node) -> float:
    _left, top, _w, h = n["box"]
    return top + h / 2


def _median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _cluster(nodes: list[Node], coord, tol: float | None,
             span_index: int) -> list[list[Node]]:
    """Greedily cluster nodes whose ``coord`` centres fall within ``tol``.

    ``span_index`` selects which box dimension (2=width, 3=height) sets the
    default tolerance, so row/column tolerances adapt to element size.
    """
    if not nodes:
        return []
    if tol is None:
        tol = max(0.012, 0.5 * _median([n["box"][span_index] for n in nodes]))

    clusters: list[dict[str, Any]] = []
    for n in sorted(nodes, key=coord):
        for cl in clusters:
            if abs(coord(n) - cl["center"]) <= tol:
                cl["members"].append(n)
                cl["center"] = sum(coord(m) for m in cl["members"]) / len(cl["members"])
                break
        else:
            clusters.append({"center": coord(n), "members": [n]})
    return [cl["members"] for cl in clusters]


def group_rows(nodes: list[Node], tol: float | None = None) -> list[list[Node]]:
    """Group nodes into reading-order rows (top→bottom), each ordered left→right.

    Two nodes share a row when their vertical centres are within ``tol`` (default
    derived from the median node height). This fuses elements of *different*
    kinds — e.g. a menu label and a toggle glyph — onto one row.
    """
    rows = _cluster(nodes, _cy, tol, span_index=3)
    for row in rows:
        row.sort(key=_cx)
    rows.sort(key=lambda r: _cy(r[0]))
    return rows


def align_columns(nodes: list[Node], tol: float | None = None,
                  min_members: int = 2) -> list[list[Node]]:
    """Group vertically-aligned nodes into columns (each ordered top→bottom).

    A column with two or more members is the relation that binds, e.g., a chart
    value to the axis label beneath it. Columns of one are dropped as
    uninformative.
    """
    cols = _cluster(nodes, _cx, tol, span_index=2)
    cols = [c for c in cols if len(c) >= min_members]
    for col in cols:
        col.sort(key=_cy)
    cols.sort(key=lambda c: _cx(c[0]))
    return cols


def containment(nodes: list[Node], tol: float = 0.01) -> list[tuple[Node, list[Node]]]:
    """Find (container, [contained]) pairs by strict box enclosure.

    A node contains another when its box encloses the other's (within ``tol``)
    and is strictly larger in area — so a word reads as *inside* the button or
    shape it sits on, never the reverse.
    """
    pairs: list[tuple[Node, list[Node]]] = []
    for a in nodes:
        al, at, aw, ah = a["box"]
        a_area = aw * ah
        inside: list[Node] = []
        for b in nodes:
            if b is a:
                continue
            bl, bt, bw, bh = b["box"]
            if (bl >= al - tol and bt >= at - tol
                    and bl + bw <= al + aw + tol and bt + bh <= at + ah + tol
                    and a_area > bw * bh):
                inside.append(b)
        if inside:
            inside.sort(key=lambda n: (_cy(n), _cx(n)))
            pairs.append((a, inside))
    return pairs
