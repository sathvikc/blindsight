"""Held-out tests for OCR reading-order reconstruction.

These exercise the pure word-ordering logic with synthetic word records, so
they need no Tesseract binary and don't depend on the showcase images. The
point is to prove the ordering generalises: words handed over out of spatial
order are reassembled top-to-bottom, left-to-right with line structure intact.
"""

from __future__ import annotations

from blindsight.modules.ocr import _order_lines


def _word(text, line, left, top):
    return {"text": text, "left": left, "top": top,
            "width": 10 * len(text), "height": 20, "line": line}


def _texts(records):
    return [r["text"] for r in records]


def test_words_within_a_line_sort_left_to_right():
    words = [
        _word("WORLD", (0, 0, 0), 120, 10),
        _word("HELLO", (0, 0, 0), 10, 10),
    ]
    assert _texts(_order_lines(words)) == ["HELLO WORLD"]


def test_lines_sort_top_to_bottom_regardless_of_input_order():
    words = [
        _word("third", (0, 0, 2), 10, 300),
        _word("first", (0, 0, 0), 10, 10),
        _word("second", (0, 0, 1), 10, 150),
    ]
    assert _texts(_order_lines(words)) == ["first", "second", "third"]


def test_multiword_multiline_block_reads_in_order():
    # Two lines, words deliberately shuffled in the input.
    words = [
        _word("Cart", (1, 0, 0), 80, 20),
        _word("Blue", (1, 0, 0), 10, 20),
        _word("Market", (1, 0, 0), 150, 20),
        _word("687.75", (1, 0, 1), 120, 60),
        _word("TOTAL", (1, 0, 1), 10, 60),
    ]
    assert _texts(_order_lines(words)) == ["Blue Cart Market", "TOTAL 687.75"]


def test_separate_blocks_order_by_vertical_position():
    # A lower block given first; reading order must still be top block first.
    words = [
        _word("footer", (2, 0, 0), 10, 500),
        _word("header", (0, 0, 0), 10, 5),
    ]
    assert _texts(_order_lines(words)) == ["header", "footer"]


def test_line_boxes_cover_their_words():
    words = [
        _word("HELLO", (0, 0, 0), 10, 10),
        _word("WORLD", (0, 0, 0), 120, 10),
    ]
    record = _order_lines(words)[0]
    assert record["left"] == 10
    assert record["right"] == 120 + 10 * len("WORLD")
    assert record["top"] == 10
    assert record["bottom"] == 30


def test_empty_input_yields_no_lines():
    assert _order_lines([]) == []
