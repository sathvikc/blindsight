"""Extraction modules.

Each module exposes: NAME:  str                      machine key TITLE: str                      section label run(ctx) -> dict                produce serializable data (may raise ModuleUnavailable for missing deps) render(data) -> list[str]       turn data into text body lines

Modules are intentionally independent: one failing never aborts the others.
"""

from . import (codes, colors, exif, faces, ocr, regions, shapes, stats,
               structure, tables)

# Output order is deliberate: cheap factual signals first (stats, text),
# then visual/structural signals, then metadata. Tables sit right after OCR
# because they are the same kind of signal — verbatim text, with its
# row/column associations preserved.
REGISTRY = [stats, ocr, tables, colors, regions, structure, shapes, faces,
            codes, exif]

__all__ = ["REGISTRY"]
