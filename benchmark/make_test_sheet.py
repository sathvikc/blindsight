#!/usr/bin/env python3
"""Build the human grading artifacts for the accuracy benchmark.

Reads the ground truth (ground_truth.json) and the generated descriptors
(results/*.descriptor.txt) and emits two companion files:

  * ``test_sheet.md``  — readable worksheet. For every image it shows the
                         descriptor, each question, the correct answer, and
                         whether the question is factual or perceptual. You run
                         each question twice — once against the descriptor text
                         (condition A) and once against the real image with a
                         multimodal model (condition B) — and decide if each
                         answer is right.

  * ``scorecard.csv``  — the machine-readable half. One row per question with
                         two blank grade columns, ``descriptor_grade`` and
                         ``image_grade``. Fill each with 1 (correct), 0 (wrong),
                         or 0.5 (partial). Then run score.py on it.

Splitting "what to grade" (this script) from "tally the grades" (score.py) keeps
the workflow honest: you commit to a grade per question before seeing the totals.

Usage:
    python benchmark/make_test_sheet.py \
        --ground-truth benchmark/ground_truth.json \
        --results examples/results \
        --out benchmark
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def _load_ground_truth(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    # Drop documentation keys (any leading-underscore key).
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _descriptor_text(results_dir: Path, image_name: str) -> str:
    stem = Path(image_name).stem
    path = results_dir / f"{stem}.descriptor.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8").rstrip()
    return "(no descriptor found — run run_benchmark.py first)"


def _write_test_sheet(out: Path, ground_truth: dict, results_dir: Path) -> None:
    lines: list[str] = []
    lines.append("# Benchmark test sheet")
    lines.append("")
    lines.append(
        "For each question, answer it **twice** and grade each answer in "
        "`scorecard.csv`:")
    lines.append("")
    lines.append(
        "- **Condition A (descriptor):** paste the descriptor below (or the "
        "matching `results/<name>.packet.txt`) into a text-only model and "
        "answer from that alone.")
    lines.append(
        "- **Condition B (image):** give the real image to a multimodal model "
        "as the control.")
    lines.append("")
    lines.append(
        "Grade each answer `1` (correct), `0` (wrong), or `0.5` (partial) "
        "against the correct answer shown here. `type` tells you whether the "
        "fact is *factual* (text should be able to carry it) or *perceptual* "
        "(expected to need the pixels).")
    lines.append("")

    for image_name, questions in ground_truth.items():
        lines.append(f"## {image_name}")
        lines.append("")
        lines.append("<details><summary>descriptor</summary>")
        lines.append("")
        lines.append("```")
        lines.append(_descriptor_text(results_dir, image_name))
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")
        lines.append("| # | type | question | correct answer |")
        lines.append("|---|---|---|---|")
        for i, q in enumerate(questions, 1):
            qt = q["q"].replace("|", "\\|")
            at = q["a"].replace("|", "\\|")
            lines.append(f"| {i} | {q['type']} | {qt} | {at} |")
        lines.append("")

    (out / "test_sheet.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_scorecard(out: Path, ground_truth: dict) -> None:
    path = out / "scorecard.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "image", "q_index", "type", "question", "correct_answer",
            "descriptor_grade", "image_grade",
        ])
        for image_name, questions in ground_truth.items():
            for i, q in enumerate(questions, 1):
                writer.writerow([
                    image_name, i, q["type"], q["q"], q["a"], "", "",
                ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ground-truth", default="benchmark/ground_truth.json")
    parser.add_argument("--results", default="examples/results")
    parser.add_argument("--out", default="benchmark")
    args = parser.parse_args(argv)

    gt_path = Path(args.ground_truth)
    if not gt_path.is_file():
        print(f"error: no ground truth at {gt_path}", file=sys.stderr)
        return 1
    ground_truth = _load_ground_truth(gt_path)
    results_dir = Path(args.results)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    _write_test_sheet(out, ground_truth, results_dir)
    _write_scorecard(out, ground_truth)

    n_images = len(ground_truth)
    n_q = sum(len(v) for v in ground_truth.values())
    print(f"Wrote {out / 'test_sheet.md'} and {out / 'scorecard.csv'} "
          f"({n_images} images, {n_q} questions).")
    print("Fill descriptor_grade and image_grade in scorecard.csv (1 / 0 / 0.5), "
          "then run: python benchmark/score.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
