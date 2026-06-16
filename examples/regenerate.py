#!/usr/bin/env python3
"""Regenerate examples/results/ from examples/images/.

Run from anywhere; paths are resolved relative to this file. Use after any
change that affects descriptor output, then commit the refreshed fixtures —
tests/test_example_fixtures.py fails if the committed results drift from
what the code actually produces.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    return subprocess.call([
        sys.executable, str(ROOT / "benchmark" / "run_benchmark.py"),
        "--images", str(ROOT / "examples" / "images"),
        "--out", str(ROOT / "examples" / "results"),
        "--questions", str(ROOT / "examples" / "questions.json"),
    ])


if __name__ == "__main__":
    raise SystemExit(main())
