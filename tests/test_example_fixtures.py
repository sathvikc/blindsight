"""Guard the committed example fixtures against silent drift.

examples/results/*.txt are documentation: they show users exactly what the
tool produces. Nothing else asserts the tool still reproduces them, so any
output change silently turns them stale. This smoke test re-extracts two
showcase images and compares the *deterministic* sections against the
committed descriptors. OCR (Tesseract-version dependent) and Faces are
deliberately excluded so the test is stable across environments.

When this fails after an intentional output change, refresh the fixtures:

    python examples/regenerate.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from blindsight import extract

ROOT = Path(__file__).resolve().parent.parent

_STABLE_SECTIONS = ("Stats", "Colors", "Regions", "Codes")


def _sections(text: str) -> dict[str, list[str]]:
    """Parse descriptor text into {section title: body lines}."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            sections[current] = []
        elif current is not None and line.strip():
            sections[current].append(line.strip())
        elif not line.strip():
            current = None
    return sections


@pytest.mark.parametrize("name", ["qr_code", "bar_chart"])
def test_committed_descriptor_matches_current_output(name):
    image = ROOT / "examples" / "images" / f"{name}.png"
    fixture = ROOT / "examples" / "results" / f"{name}.descriptor.txt"
    assert fixture.exists(), "fixture missing - run examples/regenerate.py"

    committed = _sections(fixture.read_text(encoding="utf-8"))
    current = _sections(extract(str(image)).to_text())

    for section in _STABLE_SECTIONS:
        assert current.get(section) == committed.get(section), (
            f"{name}: [{section}] drifted from the committed fixture - "
            "if the change is intentional, run examples/regenerate.py "
            "and commit the refreshed results"
        )
