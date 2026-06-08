"""Layout — the spatial 'where' layer that fuses other modules' detections.

Where every other module reports *what* it found independently, this one reports
*how the findings relate in space*: reading-order rows, vertically-aligned
columns, and containment. It consumes the boxes the OCR, shapes, and faces
modules have already stashed on the context (``ctx.results``), so it adds no new
detection cost — only geometry. The relations it surfaces (value-over-label,
word-inside-button, a row that breaks a repeating pattern) are exactly the
*relational* facts a flat per-module listing loses.

Nothing here uses machine learning; see :mod:`blindsight.layout` for the engine.
"""

from __future__ import annotations

from typing import Any

from ..context import ImageContext
from ..layout import align_columns, containment, group_rows

NAME = "layout"
TITLE = "Layout"

_MAX_ROWS = 20
_MAX_COLUMNS = 12


def _collect_nodes(ctx: ImageContext) -> list[dict[str, Any]]:
    """Build typed nodes from detections earlier modules left on the context."""
    nodes: list[dict[str, Any]] = []

    ocr = ctx.results.get("ocr") or {}
    for i, w in enumerate(ocr.get("words", [])):
        nodes.append({"id": f"t{i}", "kind": "text",
                      "label": w["text"], "box": w["box"]})

    shapes = ctx.results.get("shapes") or {}
    for i, s in enumerate(shapes.get("shapes", [])):
        # Noise-sized contours create spurious containment; only real frames
        # and buttons (medium/large) earn a place in the spatial graph.
        if "box" in s and s.get("size") != "small":
            nodes.append({"id": f"s{i}", "kind": "shape",
                          "label": s["shape"], "box": s["box"]})

    faces = ctx.results.get("faces") or {}
    for i, box in enumerate(faces.get("boxes", [])):
        nodes.append({"id": f"f{i}", "kind": "face", "label": "face", "box": box})

    return nodes


def _column_class(col: list[dict[str, Any]], row_of: dict[int, int],
                  n_rows: int) -> str:
    """Classify an alignment column by the kind of signal it carries.

    * ``"local"`` — spans at most half the rows: a value over its axis label, a
      caption under a figure. A direct binding.
    * ``"break"`` — a mostly-filled run that *skips* an *interior* row its
      neighbours fill: a toggle present on every menu item but one. The gap must
      be bracketed by presence (rows with the element both above and below it);
      a gap at the first or last row is left as ``"grid"`` on purpose, because
      geometry cannot tell a list item missing its control from a header or
      button that never had one — flagging those would invent false breaks.
    * ``"grid"`` — a contiguous full-height column. On its own this is just a
      left margin restating the reading order; only kept when several run in
      parallel (a real table), which the caller decides.
    * ``"drop"`` — degenerate (fewer than two rows) or scattered noise.
    """
    rows_hit = sorted({row_of[id(n)] for n in col if id(n) in row_of})
    if len(rows_hit) < 2:
        return "drop"            # a vertical column must span at least two rows
    if n_rows < 2:
        return "local"
    span = rows_hit[-1] - rows_hit[0] + 1
    gap = span - len(rows_hit)
    if len(rows_hit) / n_rows <= 0.5:
        return "local"
    if 1 <= gap <= len(rows_hit):
        return "break"
    if gap == 0:
        return "grid"
    return "drop"                # scattered across distant unrelated rows


def _classify_columns(
    cols: list[list[dict[str, Any]]], row_of: dict[int, int], n_rows: int
) -> tuple[list[list[dict[str, Any]]], list[list[dict[str, Any]]]]:
    """Route aligned columns into value-bindings versus pattern-breaks.

    Returns ``(columns, breaks)``, each left-to-right:

    * *columns* — alignment bindings to list verbatim (a value over its axis
      label; a table grid where two or more full-height columns run parallel).
    * *breaks* — columns that recur down most rows yet *skip* one. The gap is
      the signal, so these are handed back whole for the caller to describe by
      *which* row is missing, not as a bare list of members.

    Full-height columns standing alone are dropped — a lone left margin merely
    restates the reading order.
    """
    klass = [_column_class(c, row_of, n_rows) for c in cols]
    grid_is_table = klass.count("grid") >= 2
    columns, breaks = [], []
    for c, k in zip(cols, klass):
        if k == "local" or (k == "grid" and grid_is_table):
            columns.append(c)
        elif k == "break":
            breaks.append(c)
    return columns, breaks


def _common_label(col: list[dict[str, Any]]) -> str:
    """The element that recurs down a column (its most frequent label)."""
    labels = [n["label"] for n in col]
    return max(set(labels), key=labels.count)


def _describe_break(col: list[dict[str, Any]], row_of: dict[int, int],
                    rows: list[list[str]]) -> dict[str, Any]:
    """Name the recurring element and the row(s) where it goes missing.

    A row is identified by its leading (left-most) label — the menu item or
    field name a reader would use to point at it.
    """
    rows_hit = sorted({row_of[id(n)] for n in col if id(n) in row_of})
    absent = [r for r in range(rows_hit[0], rows_hit[-1] + 1) if r not in rows_hit]
    missing = [rows[r][0] for r in absent if rows[r]]
    return {"element": _common_label(col), "missing": missing}


def run(ctx: ImageContext) -> dict[str, Any]:
    nodes = _collect_nodes(ctx)
    if not nodes:
        return {"node_count": 0, "kinds": {}, "rows": [], "columns": [],
                "breaks": [], "contains": []}

    kinds: dict[str, int] = {}
    for n in nodes:
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1

    # Rows and columns describe how *labelled* content (text, faces) lays out.
    # Structural shapes carry no label of their own, so they take part only in
    # containment — as the button/frame a word sits inside — where they add
    # signal rather than noise.
    labelled = [n for n in nodes if n["kind"] != "shape"]

    row_nodes = group_rows(labelled)
    rows = [[n["label"] for n in row] for row in row_nodes]

    row_of = {id(n): i for i, row in enumerate(row_nodes) for n in row}
    n_rows = len(row_nodes)

    # In running-text documents (most rows are multi-word phrases) vertical
    # alignment is incidental — reading order already carries the meaning, so
    # columns would be noise. Column relations are reserved for label-dominated
    # layouts: charts, forms, menus, diagrams.
    multiword = sum(1 for row in row_nodes if len(row) >= 3)
    is_document = n_rows >= 2 and multiword / n_rows > 0.5
    columns: list[list[str]] = []
    breaks: list[dict[str, Any]] = []
    if not is_document:
        binding_cols, break_cols = _classify_columns(
            align_columns(labelled), row_of, n_rows)
        columns = [[n["label"] for n in col] for col in binding_cols]
        breaks = [d for col in break_cols
                  if (d := _describe_break(col, row_of, rows))["missing"]]

    # A container is a frame holding labels (a button around its caption, a plot
    # area around its values); a text label is never itself a container.
    contains = [
        {"container": c["label"], "inside": [n["label"] for n in members]}
        for c, members in containment(nodes)
        if c["kind"] in ("shape", "face")
    ]

    return {
        "node_count": len(nodes),
        "kinds": kinds,
        "rows": rows[:_MAX_ROWS],
        "columns": columns[:_MAX_COLUMNS],
        "breaks": breaks[:_MAX_COLUMNS],
        "contains": contains,
    }


def render(data: dict[str, Any]) -> list[str]:
    if data["node_count"] == 0:
        return ["none"]

    kinds = ", ".join(f"{k} {v}" for k, v in sorted(data["kinds"].items()))
    out = [f"nodes: {data['node_count']} ({kinds})"]

    if data["rows"]:
        out.append("reading order (rows, top→bottom):")
        for i, row in enumerate(data["rows"], 1):
            out.append(f"  {i}. {' '.join(row)}")

    if data["columns"]:
        out.append("aligned columns (top→bottom):")
        for col in data["columns"]:
            out.append(f"  - {' / '.join(col)}")

    if data.get("breaks"):
        out.append("pattern breaks (a repeating element with a gap):")
        for b in data["breaks"]:
            missing = ", ".join(b["missing"])
            out.append(
                f"  - '{b['element']}' aligns down a column on other rows but "
                f"is missing at: {missing}")

    if data["contains"]:
        out.append("contains:")
        for c in data["contains"]:
            out.append(f"  - {c['container']} ⊃ {', '.join(c['inside'])}")

    return out
