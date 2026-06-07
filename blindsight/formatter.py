"""Render an :class:`ImageDescriptor` to text or JSON.

The text format is a single block with one ``[Section]`` per module — compact,
deterministic, and easy for a language model to parse. The JSON format mirrors
the same structure for programmatic use.
"""

from __future__ import annotations

from typing import Any

from .descriptor import ImageDescriptor

_HEADER = "=== IMAGE DESCRIPTOR ==="
_FOOTER = "========================="


def to_text(descriptor: ImageDescriptor) -> str:
    available = sum(1 for r in descriptor.results if r.available)
    lines = [
        _HEADER,
        f"source: {descriptor.source}",
        f"size: {descriptor.width}x{descriptor.height}",
        f"modules: {available}/{len(descriptor.results)} available",
        "",
    ]
    for result in descriptor.results:
        lines.extend(result.to_lines())
        lines.append("")
    lines.append(_FOOTER)
    return "\n".join(lines)


def to_json(descriptor: ImageDescriptor) -> dict[str, Any]:
    return {
        "source": descriptor.source,
        "width": descriptor.width,
        "height": descriptor.height,
        "modules": {
            result.name: {
                "title": result.title,
                "available": result.available,
                "note": result.note,
                "data": result.data,
            }
            for result in descriptor.results
        },
    }
