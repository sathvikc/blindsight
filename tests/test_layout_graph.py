"""Held-out tests for the spatial relation engine.

These exercise the pure geometry with synthetic nodes — no images, no detector
dependencies — so they prove the relations generalise rather than fitting the
showcase set. Boxes are (left, top, width, height) in the unit square.
"""

from __future__ import annotations

from blindsight.layout import align_columns, containment, group_rows


def _node(label, left, top, w=0.05, h=0.04, kind="text"):
    return {"kind": kind, "label": label, "box": (left, top, w, h)}


# --- rows -------------------------------------------------------------------

def test_rows_order_top_to_bottom_and_left_to_right():
    # Deliberately shuffled input.
    nodes = [
        _node("B", 0.50, 0.10),
        _node("A", 0.10, 0.10),
        _node("C", 0.10, 0.50),
    ]
    rows = group_rows(nodes)
    assert [[n["label"] for n in r] for r in rows] == [["A", "B"], ["C"]]


def test_rows_fuse_different_kinds_on_one_line():
    # A menu label and a toggle glyph at the same height belong on one row.
    nodes = [
        _node("Account", 0.10, 0.20),
        _node("@", 0.80, 0.205, w=0.03, h=0.03),
    ]
    rows = group_rows(nodes)
    assert [[n["label"] for n in r] for r in rows] == [["Account", "@"]]


def test_row_missing_an_element_is_visible_as_a_short_row():
    # Three list rows; the middle one lacks the trailing glyph its siblings have.
    nodes = [
        _node("Account", 0.10, 0.10), _node("@", 0.80, 0.10, w=0.03, h=0.03),
        _node("Privacy", 0.10, 0.30),
        _node("Storage", 0.10, 0.50), _node("@", 0.80, 0.50, w=0.03, h=0.03),
    ]
    rows = [[n["label"] for n in r] for r in group_rows(nodes)]
    assert rows == [["Account", "@"], ["Privacy"], ["Storage", "@"]]


# --- columns ----------------------------------------------------------------

def test_columns_bind_value_over_label():
    # A bar chart: four values in a row, four quarter labels below, aligned.
    nodes = [
        _node("280", 0.10, 0.10), _node("200", 0.35, 0.10),
        _node("160", 0.60, 0.10), _node("120", 0.85, 0.10),
        _node("Q1", 0.10, 0.80), _node("Q2", 0.35, 0.80),
        _node("Q3", 0.60, 0.80), _node("Q4", 0.85, 0.80),
    ]
    cols = [[n["label"] for n in c] for c in align_columns(nodes)]
    assert cols == [["280", "Q1"], ["200", "Q2"], ["160", "Q3"], ["120", "Q4"]]


def test_columns_drop_unaligned_singletons():
    nodes = [_node("alone", 0.10, 0.10), _node("solo", 0.90, 0.50)]
    assert align_columns(nodes) == []


# --- containment ------------------------------------------------------------

def test_containment_word_inside_button():
    button = _node("rectangle", 0.60, 0.80, w=0.30, h=0.12, kind="shape")
    word = _node("Save", 0.68, 0.83, w=0.12, h=0.05)
    elsewhere = _node("Header", 0.10, 0.05)
    pairs = containment([button, word, elsewhere])
    assert len(pairs) == 1
    container, inside = pairs[0]
    assert container["label"] == "rectangle"
    assert [n["label"] for n in inside] == ["Save"]


def test_containment_is_directional_not_mutual():
    big = _node("big", 0.10, 0.10, w=0.50, h=0.50, kind="shape")
    small = _node("small", 0.20, 0.20, w=0.10, h=0.10)
    pairs = containment([big, small])
    # Only the larger box contains the smaller — never the reverse.
    assert len(pairs) == 1
    assert pairs[0][0]["label"] == "big"


def test_empty_input_is_safe():
    assert group_rows([]) == []
    assert align_columns([]) == []
    assert containment([]) == []


# --- module-level relation filtering ----------------------------------------

from blindsight.context import ImageContext
from blindsight.modules.layout import _classify_columns, _column_class, run


def _ctx(words):
    """Minimal context carrying only OCR word boxes for the layout module."""
    return ImageContext(path="x", pil=None, rgb=None, gray=None,
                        width=1, height=1, results={"ocr": {"words": words}})


def _word(text, left, top, w=0.05, h=0.04):
    return {"text": text, "conf": 90.0, "box": (left, top, w, h)}


def test_class_local_binding():
    # Two items aligned in a column, touching 2 of 6 rows — a value/label bind.
    a, b = _node("280", 0.2, 0.1), _node("Q1", 0.2, 0.8)
    row_of = {id(a): 1, id(b): 5}
    assert _column_class([a, b], row_of, n_rows=6) == "local"
    # A lone local binding is kept as a column, never as a break.
    cols, breaks = _classify_columns([[a, b]], row_of, n_rows=6)
    assert cols == [[a, b]] and breaks == []


def test_class_pattern_break_routed_to_breaks():
    # A control on rows 0,1,3,4 — skips row 2; the skip is the signal.
    ns = [_node(str(i), 0.8, y) for i, y in enumerate((0.1, 0.2, 0.4, 0.5))]
    row_of = {id(ns[0]): 0, id(ns[1]): 1, id(ns[2]): 3, id(ns[3]): 4}
    assert _column_class(ns, row_of, n_rows=6) == "break"
    cols, breaks = _classify_columns([ns], row_of, n_rows=6)
    # Breaks leave the verbatim-columns list and travel their own channel.
    assert cols == [] and breaks == [ns]


def test_class_left_margin_dropped():
    # Six items down a contiguous left margin of six rows — restates the rows.
    ns = [_node("x", 0.1, i * 0.15) for i in range(6)]
    row_of = {id(n): i for i, n in enumerate(ns)}
    assert _column_class(ns, row_of, n_rows=6) == "grid"
    # A single full-height column is a margin, not a table — dropped entirely.
    cols, breaks = _classify_columns([ns], row_of, n_rows=6)
    assert cols == [] and breaks == []


def test_two_parallel_grids_kept_as_table():
    # Two full-height columns running in parallel are a real table grid.
    left = [_node("L", 0.1, i * 0.15) for i in range(6)]
    right = [_node("R", 0.6, i * 0.15) for i in range(6)]
    row_of = {id(n): i for i, n in enumerate(left)}
    row_of.update({id(n): i for i, n in enumerate(right)})
    cols, breaks = _classify_columns([left, right], row_of, n_rows=6)
    assert cols == [left, right] and breaks == []


def test_class_same_row_pair_dropped():
    a, b = _node("YOUR", 0.4, 0.5), _node("UI", 0.4, 0.5)
    row_of = {id(a): 4, id(b): 4}
    assert _column_class([a, b], row_of, n_rows=5) == "drop"
    cols, breaks = _classify_columns([[a, b]], row_of, n_rows=5)
    assert cols == [] and breaks == []


def test_break_names_the_missing_row():
    # A trailing glyph recurs on four list rows; one row (Privacy) lacks it.
    # The break must be reported by the *name* of the row where it goes missing.
    words = [
        _word("Account", 0.1, 0.10), _word("@", 0.85, 0.10, w=0.03, h=0.03),
        _word("Notifications", 0.1, 0.25), _word("@", 0.85, 0.25, w=0.03, h=0.03),
        _word("Privacy", 0.1, 0.40),
        _word("Appearance", 0.1, 0.55), _word("@", 0.85, 0.55, w=0.03, h=0.03),
        _word("Storage", 0.1, 0.70), _word("@", 0.85, 0.70, w=0.03, h=0.03),
    ]
    out = run(_ctx(words))
    assert out["breaks"], "the toggle gap should surface as a pattern break"
    b = out["breaks"][0]
    assert b["element"] == "@"
    assert b["missing"] == ["Privacy"]
    # And the verbatim @/@/@/@ column no longer pollutes the bindings list.
    assert ["@", "@", "@", "@"] not in out["columns"]


def test_break_generalises_to_other_shape_symbol_and_position():
    # A different layout entirely: a checklist whose status word "done" recurs,
    # with the gap at a different interior row than app_ui and a word (not a
    # glyph) as the element. The mechanism must not depend on the app_ui shape,
    # the particular symbol, or the exact gap position.
    words = [
        _word("Design", 0.1, 0.10), _word("done", 0.80, 0.10),
        _word("Build", 0.1, 0.25),
        _word("Test", 0.1, 0.40), _word("done", 0.80, 0.40),
        _word("Ship", 0.1, 0.55), _word("done", 0.80, 0.55),
        _word("Deploy", 0.1, 0.70), _word("done", 0.80, 0.70),
    ]
    out = run(_ctx(words))
    assert out["breaks"]
    b = out["breaks"][0]
    assert b["element"] == "done"
    assert b["missing"] == ["Build"]


def test_edge_gap_is_conservatively_not_flagged():
    # The recurring element is absent only at the FIRST row. Pure geometry can't
    # tell "a list item missing its control" from "a header/title that never had
    # one", so an edge gap is deliberately NOT reported — this is what stops the
    # app_ui "Save" button (a trailing row with no '@') being called a broken
    # toggle. Breaks are claimed only when the gap is bracketed by presence.
    words = [
        _word("Heading", 0.1, 0.10),
        _word("Build", 0.1, 0.25), _word("x", 0.80, 0.25, w=0.03, h=0.03),
        _word("Test", 0.1, 0.40), _word("x", 0.80, 0.40, w=0.03, h=0.03),
        _word("Ship", 0.1, 0.55), _word("x", 0.80, 0.55, w=0.03, h=0.03),
    ]
    out = run(_ctx(words))
    assert out["breaks"] == []


def test_break_reports_multiple_missing_rows():
    # Two adjacent rows lack the recurring element — both must be named.
    words = [
        _word("R0", 0.1, 0.10), _word("x", 0.80, 0.10, w=0.03, h=0.03),
        _word("R1", 0.1, 0.25), _word("x", 0.80, 0.25, w=0.03, h=0.03),
        _word("R2", 0.1, 0.40),
        _word("R3", 0.1, 0.55),
        _word("R4", 0.1, 0.70), _word("x", 0.80, 0.70, w=0.03, h=0.03),
        _word("R5", 0.1, 0.85), _word("x", 0.80, 0.85, w=0.03, h=0.03),
    ]
    out = run(_ctx(words))
    assert out["breaks"]
    assert out["breaks"][0]["missing"] == ["R2", "R3"]


def test_complete_column_is_not_a_break():
    # The recurring element is present on EVERY row — no gap, so no break and
    # (as a lone full-height column) no spurious binding either.
    words = [
        _word(f"Row{i}", 0.1, 0.10 + i * 0.15) for i in range(5)
    ] + [
        _word("x", 0.80, 0.10 + i * 0.15, w=0.03, h=0.03) for i in range(5)
    ]
    out = run(_ctx(words))
    assert out["breaks"] == []


def test_document_layout_suppresses_columns():
    # Mostly multi-word rows (a receipt/prose) → reading order only, no columns.
    words = [
        _word("Milk", 0.1, 0.1), _word("x2", 0.4, 0.1), _word("90.00", 0.8, 0.1),
        _word("Eggs", 0.1, 0.3), _word("x1", 0.4, 0.3), _word("120.00", 0.8, 0.3),
        _word("TOTAL", 0.1, 0.5), _word("Rs", 0.4, 0.5), _word("687.75", 0.8, 0.5),
    ]
    out = run(_ctx(words))
    assert out["rows"]  # reading order is still produced
    assert out["columns"] == []  # vertical alignments suppressed in documents


def test_label_layout_keeps_columns():
    # Short-label rows (a chart): value over axis label must bind via a column.
    words = [
        _word("280", 0.2, 0.1), _word("160", 0.6, 0.1),
        _word("Q1", 0.2, 0.8), _word("Q2", 0.6, 0.8),
    ]
    out = run(_ctx(words))
    assert ["280", "Q1"] in out["columns"]
    assert ["160", "Q2"] in out["columns"]
