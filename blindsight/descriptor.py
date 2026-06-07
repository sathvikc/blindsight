"""Core data model for an extracted image description.

A descriptor is an ordered collection of module results. Each module knows how
to render its own data to text, which keeps presentation next to the logic that
produces it and lets the descriptor stay agnostic about module internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ModuleResult:
    """Outcome of a single extraction module.

    Attributes:
        name: Stable machine key (used in JSON output).
        title: Human/LLM facing section label, e.g. ``"Colors"``.
        available: Whether the module ran. False means a missing dependency or
            an unrecoverable error — never a crash that aborts extraction.
        data: Serializable payload produced by the module.
        note: Short explanation, typically why a module is unavailable.
        render: Callable turning ``data`` into text lines for the section body.
    """

    name: str
    title: str
    available: bool
    data: dict[str, Any] = field(default_factory=dict)
    note: str | None = None
    render: Callable[[dict[str, Any]], list[str]] | None = None

    def to_lines(self) -> list[str]:
        """Render this section, including its ``[Title]`` header."""
        header = f"[{self.title}]"
        if not self.available:
            reason = self.note or "not available"
            return [header, f"  unavailable: {reason}"]
        if self.render is None:
            return [header]
        body = self.render(self.data)
        if not body:
            return [header, "  none"]
        return [header, *(f"  {line}" for line in body)]


@dataclass
class ImageDescriptor:
    """Full descriptor for one image."""

    source: str
    width: int
    height: int
    results: list[ModuleResult] = field(default_factory=list)

    def get(self, name: str) -> ModuleResult | None:
        """Return the result for a module by machine name, if present."""
        for result in self.results:
            if result.name == name:
                return result
        return None

    def to_text(self) -> str:
        """Render the descriptor as a single LLM-friendly text block."""
        from .formatter import to_text

        return to_text(self)

    def to_json(self) -> dict[str, Any]:
        """Render the descriptor as a serializable dictionary."""
        from .formatter import to_json

        return to_json(self)
