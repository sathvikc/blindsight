#!/usr/bin/env python3
"""Tally a filled-in scorecard into the benchmark's headline numbers.

Reads ``scorecard.csv`` (produced by make_test_sheet.py and graded by you) and
prints the result the project actually claims: how the descriptor-only path
compares to the real-image control, split by whether the question was *factual*
or *perceptual*.

The thesis is **not** "text beats vision". It is "on the factual subset, text is
~as good as vision for a fraction of the cost". So the factual-row accuracy is
the number that matters; the perceptual row is expected to be low and is there to
prove the tool is honest about its ceiling.

Grades per cell: 1 (correct), 0 (wrong), 0.5 (partial). Blank cells are treated
as ungraded and skipped (and reported), so a partially graded sheet still tallies.

Usage:
    python benchmark/score.py                       # reads benchmark/scorecard.csv
    python benchmark/score.py --scorecard path.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def _parse_grade(raw: str):
    raw = (raw or "").strip()
    if raw == "":
        return None
    try:
        val = float(raw)
    except ValueError:
        return None
    return val


def _pct(num: float, den: float) -> str:
    return f"{num / den:.0%}" if den else "  -"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--scorecard", default="benchmark/scorecard.csv")
    args = parser.parse_args(argv)

    path = Path(args.scorecard)
    if not path.is_file():
        print(f"error: no scorecard at {path}", file=sys.stderr)
        print("Run make_test_sheet.py first, then grade it.", file=sys.stderr)
        return 1

    # buckets[type][condition] = [graded_count, score_sum]
    buckets = {
        "factual": {"descriptor": [0, 0.0], "image": [0, 0.0]},
        "perceptual": {"descriptor": [0, 0.0], "image": [0, 0.0]},
    }
    ungraded = {"descriptor": 0, "image": 0}
    total_rows = 0

    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            total_rows += 1
            qtype = (row.get("type") or "").strip()
            if qtype not in buckets:
                qtype = "factual"
            for cond, col in (("descriptor", "descriptor_grade"),
                              ("image", "image_grade")):
                grade = _parse_grade(row.get(col, ""))
                if grade is None:
                    ungraded[cond] += 1
                    continue
                buckets[qtype][cond][0] += 1
                buckets[qtype][cond][1] += grade

    def line(label: str, cond: str) -> str:
        cells = []
        for qtype in ("factual", "perceptual"):
            cnt, ssum = buckets[qtype][cond]
            cells.append(f"{_pct(ssum, cnt):>10} ({int(cnt)})")
        # overall
        cnt = sum(buckets[t][cond][0] for t in buckets)
        ssum = sum(buckets[t][cond][1] for t in buckets)
        cells.append(f"{_pct(ssum, cnt):>10} ({int(cnt)})")
        return f"{label:<20}" + "".join(f"{c:>18}" for c in cells)

    print()
    print(f"{'':<20}{'factual':>18}{'perceptual':>18}{'overall':>18}")
    print("-" * 74)
    print(line("descriptor (text)", "descriptor"))
    print(line("image (control)", "image"))
    print("-" * 74)
    print("cells show mean score (n graded). 1=correct, 0.5=partial, 0=wrong.")

    if ungraded["descriptor"] or ungraded["image"]:
        print()
        print(f"ungraded cells — descriptor: {ungraded['descriptor']}, "
              f"image: {ungraded['image']} (of {total_rows} questions each). "
              f"Fill them in scorecard.csv for a complete tally.")

    # The headline sentence.
    f = buckets["factual"]["descriptor"]
    if f[0]:
        print()
        print(f"Headline: on the {int(f[0])} graded factual questions, the "
              f"descriptor-only path scored {_pct(f[1], f[0])} — "
              "at roughly half the token cost of sending the image "
              "(see token_savings.py).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
