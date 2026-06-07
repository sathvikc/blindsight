"""Extraction orchestrator.

Loads the image once, runs every registered module against the shared context,
and collects results. A module that raises is recorded as unavailable — one
module's failure never aborts the descriptor.
"""

from __future__ import annotations

from typing import Iterable

from .context import ModuleUnavailable, load_context
from .descriptor import ImageDescriptor, ModuleResult
from .modules import REGISTRY


def extract(path: str, modules: Iterable[str] | None = None) -> ImageDescriptor:
    """Extract a structured descriptor from the image at ``path``.

    Args:
        path: Filesystem path to the image.
        modules: Optional subset of module names to run (e.g. ``["ocr",
            "colors"]``). ``None`` runs all registered modules.

    Returns:
        An :class:`ImageDescriptor` with one result per requested module.
    """
    ctx = load_context(path)
    selected = set(modules) if modules is not None else None

    results: list[ModuleResult] = []
    for module in REGISTRY:
        if selected is not None and module.NAME not in selected:
            continue
        results.append(_run_module(module, ctx))

    return ImageDescriptor(
        source=path,
        width=ctx.width,
        height=ctx.height,
        results=results,
    )


def _run_module(module, ctx) -> ModuleResult:
    try:
        data = module.run(ctx)
        return ModuleResult(
            name=module.NAME,
            title=module.TITLE,
            available=True,
            data=data,
            render=module.render,
        )
    except ModuleUnavailable as exc:
        return ModuleResult(
            name=module.NAME, title=module.TITLE,
            available=False, note=str(exc),
        )
    except Exception as exc:  # defensive: never let one module break extraction
        return ModuleResult(
            name=module.NAME, title=module.TITLE,
            available=False, note=f"error: {exc}",
        )
