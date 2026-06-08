"""Extraction modules.

Each module exposes:
    NAME:  str                      machine key
    TITLE: str                      section label
    run(ctx) -> dict                produce serializable data (may raise
                                    ModuleUnavailable for missing deps)
    render(data) -> list[str]       turn data into text body lines

Modules are intentionally independent: one failing never aborts the others.
"""

from . import codes, colors, exif, faces, layout, ocr, shapes, stats, structure

# Output order is deliberate: cheap factual signals first (stats, text), then
# visual/structural signals, then the spatial 'layout' fusion (which consumes
# ocr/shapes/faces output, so it must run after them), then metadata.
REGISTRY = [stats, ocr, colors, structure, shapes, faces, layout, codes, exif]

__all__ = ["REGISTRY"]
