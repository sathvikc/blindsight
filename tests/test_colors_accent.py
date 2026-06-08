"""Held-out tests for hue-aware accent naming and accent detection.

These swatches are synthesised here and are deliberately *not* the showcase
images, so passing them demonstrates the behaviour generalises rather than
fitting the examples. The accent feature is additive: it must surface a small
but chromatic brand colour without changing the existing dominant/grid output.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from blindsight import extract
from blindsight.colornames import accent_name, nearest_name


# --- hue-aware naming -------------------------------------------------------

@pytest.mark.parametrize("rgb,expected_substr", [
    ((245, 166, 35), "orange"),   # amber — the lume.js brand colour
    ((0, 200, 200), "cyan"),      # cyan accent
    ((30, 80, 200), "blue"),      # saturated blue
    ((220, 20, 20), "red"),       # vivid red
    ((30, 150, 60), "green"),     # green
])
def test_accent_name_follows_hue(rgb, expected_substr):
    assert expected_substr in accent_name(rgb)


def test_accent_name_keeps_desaturated_blue_as_blue_not_gray():
    # A pale, low-saturation blue must not collapse to a neutral gray name,
    # which is the failure mode of pure-RGB nearest-neighbour naming.
    name = accent_name((190, 200, 225))
    assert "blue" in name
    assert "gray" not in name


def test_accent_name_neutral_stays_neutral():
    # Near-neutral colours should still read as neutral, not a random hue.
    assert accent_name((250, 250, 250)) in {"white", "light gray"}
    assert accent_name((20, 20, 20)) in {"black", "dark gray"}
    assert "gray" in accent_name((130, 130, 132))


# --- accent detection in the colors module ----------------------------------

def _save(arr, tmp_path, name="swatch.png"):
    path = tmp_path / name
    Image.fromarray(arr.astype(np.uint8)).save(path)
    return str(path)


def test_small_high_chroma_accent_surfaces(tmp_path):
    # ~97% white field with a ~3% pure-amber stripe: the amber covers too
    # little area to be a *dominant* colour (under the 4% floor), but is the
    # brand accent.
    arr = np.full((200, 200, 3), 255, dtype=np.uint8)
    arr[:, 194:200] = (245, 166, 35)  # 3% amber stripe
    colors = extract(_save(arr, tmp_path)).get("colors")
    assert colors.available
    accent = colors.data.get("accent") or []
    names = " ".join(a["name"] for a in accent)
    assert "orange" in names

    # ...and it does NOT disturb the dominant list: white still leads.
    assert colors.data["dominant"][0]["name"] == "white"


def test_uniform_chromatic_field_adds_no_redundant_accent(tmp_path):
    # A field that is overwhelmingly one chromatic colour: that colour is
    # already dominant, so no separate accent line should be emitted.
    arr = np.full((200, 200, 3), 0, dtype=np.uint8)
    arr[:, :] = (30, 80, 200)  # all blue
    colors = extract(_save(arr, tmp_path)).get("colors")
    accent = colors.data.get("accent") or []
    assert accent == []


def test_neutral_image_has_no_accent(tmp_path):
    # A purely grayscale image must not invent a chromatic accent.
    arr = np.full((120, 120, 3), 128, dtype=np.uint8)
    arr[:, 60:] = 90
    colors = extract(_save(arr, tmp_path)).get("colors")
    accent = colors.data.get("accent") or []
    assert accent == []


def test_dominant_naming_unchanged():
    # Guard: the existing nearest_name behaviour is untouched (no regression
    # for questions that read the dominant/grid lines).
    assert nearest_name((255, 255, 255)) == "white"
    assert nearest_name((20, 30, 90)) == "navy blue"
    assert nearest_name((140, 80, 40)) == "brown"
