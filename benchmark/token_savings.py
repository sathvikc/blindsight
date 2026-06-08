#!/usr/bin/env python3
"""Measure the token cost of the descriptor versus sending the raw image.

This is the *cost* half of the benchmark and it needs no model API. It compares,
per image:

  * descriptor tokens  — the actual text Blindsight produces, counted locally
                         with tiktoken (the o200k_base encoding used by current
                         GPT-4o / 4.1 class models).
  * image tokens       — what a multimodal model would charge to ingest the same
                         image, using each vendor's published formula:
                           - OpenAI  : 85 base + 170 per 512px tile, after the
                                       documented resize (fit 2048, then shortest
                                       side to 768).
                           - Anthropic: ~ (width * height) / 750.

The descriptor's *accuracy* is scored separately (score.py). This script only
answers "how much cheaper is the text path", which is the project's premise.

Usage:
    python benchmark/token_savings.py --images examples/images
    python benchmark/token_savings.py --images examples/images \
        --results examples/results          # reuse already-generated descriptors
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}


def _count_tokens(text: str) -> int:
    """Token count via tiktoken if present, else a ~4-chars/token estimate."""
    try:
        import tiktoken
    except ImportError:
        return max(1, round(len(text) / 4))
    enc = tiktoken.get_encoding("o200k_base")
    return len(enc.encode(text))


def _openai_image_tokens(width: int, height: int) -> int:
    """OpenAI 'high detail' image token cost.

    Resize to fit within 2048x2048, then scale so the shortest side is 768,
    tile into 512px squares: 85 base + 170 per tile.
    """
    if max(width, height) > 2048:
        scale = 2048 / max(width, height)
        width, height = round(width * scale), round(height * scale)
    if min(width, height) > 768:
        scale = 768 / min(width, height)
        width, height = round(width * scale), round(height * scale)
    tiles = math.ceil(width / 512) * math.ceil(height / 512)
    return 85 + 170 * tiles


def _anthropic_image_tokens(width: int, height: int) -> int:
    """Anthropic image token estimate: (width * height) / 750.

    Anthropic resizes so the long edge is <= 1568px before this applies.
    """
    if max(width, height) > 1568:
        scale = 1568 / max(width, height)
        width, height = round(width * scale), round(height * scale)
    return math.ceil((width * height) / 750)


def _descriptor_for(image_path: Path, results_dir: Path | None) -> str:
    if results_dir is not None:
        cached = results_dir / f"{image_path.stem}.descriptor.txt"
        if cached.is_file():
            return cached.read_text(encoding="utf-8")
    from blindsight import extract
    return extract(str(image_path)).to_text()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--images", required=True, help="directory of input images")
    parser.add_argument("--results", help="dir of cached *.descriptor.txt to reuse")
    args = parser.parse_args(argv)

    images_dir = Path(args.images)
    if not images_dir.is_dir():
        print(f"error: not a directory: {images_dir}", file=sys.stderr)
        return 1
    results_dir = Path(args.results) if args.results else None

    rows = []
    tot_desc = tot_oai = tot_anthropic = 0
    for image_path in sorted(images_dir.iterdir()):
        if image_path.suffix.lower() not in _IMAGE_EXTS:
            continue
        with Image.open(image_path) as im:
            w, h = im.size
        desc_tok = _count_tokens(_descriptor_for(image_path, results_dir))
        oai_tok = _openai_image_tokens(w, h)
        anth_tok = _anthropic_image_tokens(w, h)
        rows.append((image_path.name, f"{w}x{h}", desc_tok, oai_tok, anth_tok))
        tot_desc += desc_tok
        tot_oai += oai_tok
        tot_anthropic += anth_tok

    if not rows:
        print(f"no images found in {images_dir}", file=sys.stderr)
        return 1

    name_w = max(len(r[0]) for r in rows + [("image", "", 0, 0, 0)])
    header = (f"{'image':<{name_w}}  {'size':>9}  {'descriptor':>10}  "
              f"{'OpenAI img':>10}  {'Anthr img':>9}  {'savings':>8}")
    print(header)
    print("-" * len(header))
    for name, size, d, o, a in rows:
        best_img = min(o, a)
        savings = 1 - (d / best_img) if best_img else 0
        print(f"{name:<{name_w}}  {size:>9}  {d:>10}  {o:>10}  {a:>9}  "
              f"{savings:>7.0%}")
    print("-" * len(header))
    best_img_tot = min(tot_oai, tot_anthropic)
    tot_savings = 1 - (tot_desc / best_img_tot) if best_img_tot else 0
    print(f"{'TOTAL':<{name_w}}  {'':>9}  {tot_desc:>10}  {tot_oai:>10}  "
          f"{tot_anthropic:>9}  {tot_savings:>7.0%}")

    n = len(rows)
    print()
    print(f"Across {n} images, the descriptor path uses {tot_desc} tokens versus "
          f"{tot_oai} (OpenAI) / {tot_anthropic} (Anthropic) for the raw images.")
    print(f"That is a {tot_savings:.0%} reduction against the cheaper image option "
          f"— before counting that text-only endpoints are cheaper per token too.")
    print("Note: this is input-context cost only; accuracy is scored separately "
          "(see score.py).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
