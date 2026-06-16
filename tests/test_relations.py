"""Unit tests for the relation heuristics in blindsight.relations.

These attack the function-level invariants directly with crafted band dicts —
no images needed — covering the cases that are hard or impossible to reach
through full extraction: value-equal duplicate bands, unsorted input, and
overlapping spans.
"""

from __future__ import annotations

from blindsight.relations import merge_gradients


def _band(name, hex_, top, bottom):
    return {"name": name, "hex": hex_, "top": top, "bottom": bottom}


_RUN = [
    _band("salmon", "#F39C5B", 0.00, 0.34),
    _band("salmon", "#D68C65", 0.34, 0.67),
    _band("blue", "#504192", 0.67, 1.00),
]


def test_contiguous_colour_shifting_run_becomes_gradient():
    kept, gradients = merge_gradients(list(_RUN))
    assert len(gradients) == 1
    assert gradients[0]["from"] == "salmon"
    assert gradients[0]["to"] == "blue"
    assert kept == []


def test_unsorted_input_still_detects_gradient():
    shuffled = [_RUN[2], _RUN[0], _RUN[1]]
    _, gradients = merge_gradients(shuffled)
    assert len(gradients) == 1


def test_value_equal_duplicate_is_not_dropped_with_the_run():
    # A distinct band object that happens to compare equal to a run member.
    # It overlaps the run's first strip entirely, so it cannot join the run
    # (overlap guard); identity-based filtering must keep exactly one band.
    doppelganger = dict(_RUN[0])
    kept, gradients = merge_gradients([*(dict(b) for b in _RUN), doppelganger])
    assert len(gradients) == 1
    assert len(kept) == 1, "value-equality filtering dropped the duplicate"


def test_alternating_rows_are_not_a_gradient():
    rows = [
        _band("white", "#FFFFFF", 0.00, 0.10),
        _band("white", "#E6E8EC", 0.10, 0.20),
        _band("white", "#FFFFFF", 0.20, 0.30),
        _band("white", "#E6E8EC", 0.30, 0.40),
    ]
    kept, gradients = merge_gradients(rows)
    assert gradients == []
    assert len(kept) == 4


def test_short_runs_never_merge():
    pair = _RUN[:2]
    kept, gradients = merge_gradients(list(pair))
    assert gradients == []
    assert len(kept) == 2
