#!/usr/bin/env python3
"""Batch-generate descriptors and build model-ready evaluation packets.

This harness answers one question: *how well can a text-first model answer
questions about an image from the descriptor alone, versus from the real image?*

It does not call any model API (no keys required). Instead, for each image it
produces:

  * ``<name>.descriptor.txt`` — the descriptor-only context (condition A)
  * ``<name>.packet.txt``     — a ready-to-paste prompt pairing the descriptor
                                with the ground-truth questions for that image

You then feed the packets to whichever model you are evaluating (text-only with
the descriptor, and/or multimodal with the real image as the control) and score
the answers against the ground truth you wrote.

Usage:
    python benchmark/run_benchmark.py --images path/to/images/ --out benchmark/out/

Optional ground truth: a JSON file mapping image filename -> list of questions:

    {
      "receipt.jpg": ["What is the total?", "What store is this?"],
      "chart.png":   ["How many bars are shown?"]
    }

Pass it with --questions questions.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running directly from a checkout without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from blindsight import extract  # noqa: E402

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}

_PACKET_TEMPLATE = """\
You are answering questions about an image you cannot see directly. Below is a
structured text descriptor of that image, produced by classical image analysis.
Answer each question using only the descriptor. If the descriptor does not
contain enough information, say "insufficient information".

{descriptor}

QUESTIONS:
{questions}
"""


def _iter_images(images_dir: Path):
    for path in sorted(images_dir.iterdir()):
        if path.suffix.lower() in _IMAGE_EXTS:
            yield path


def _format_questions(questions: list[str]) -> str:
    if not questions:
        return "1. Describe what this image most likely contains."
    return "\n".join(f"{i}. {q}" for i, q in enumerate(questions, 1))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images", required=True, help="directory of input images")
    parser.add_argument("--out", default="benchmark/out", help="output directory")
    parser.add_argument("--questions", help="optional ground-truth questions JSON")
    args = parser.parse_args(argv)

    images_dir = Path(args.images)
    if not images_dir.is_dir():
        print(f"error: not a directory: {images_dir}", file=sys.stderr)
        return 1

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    questions_map: dict[str, list[str]] = {}
    if args.questions:
        questions_map = json.loads(Path(args.questions).read_text(encoding="utf-8"))

    count = 0
    for image_path in _iter_images(images_dir):
        descriptor = extract(str(image_path)).to_text()
        stem = image_path.stem

        (out_dir / f"{stem}.descriptor.txt").write_text(descriptor + "\n",
                                                        encoding="utf-8")

        questions = questions_map.get(image_path.name, [])
        packet = _PACKET_TEMPLATE.format(
            descriptor=descriptor,
            questions=_format_questions(questions),
        )
        (out_dir / f"{stem}.packet.txt").write_text(packet, encoding="utf-8")
        count += 1
        print(f"processed {image_path.name}")

    print(f"\nDone. {count} image(s) -> {out_dir}/")
    print("Feed each *.packet.txt to your text model; compare against the real "
          "image as the control.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
