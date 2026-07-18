"""Third-party extraction modules, discovered via Python entry points.

Blindsight's built-in modules live in ``blindsight/modules/`` and their
output order is deliberate (see ``modules/__init__.py`` — cheap factual
signals first). Plugins are a separate, additive mechanism for third
parties to register *more* modules without forking the project or editing
``REGISTRY`` directly. A plugin package declares one or more modules under
the ``blindsight.modules`` entry-point group in its own ``pyproject.toml``::

    [project.entry-points."blindsight.modules"]
    palette_extras = "blindsight_palette_extras.module"

The value is the dotted path to a module (or any object) satisfying the
same contract every built-in module follows::

    NAME:  str                       stable machine key (JSON key, --modules value)
    TITLE: str                       "[Section]" label in text output
    run(ctx: ImageContext) -> dict   serializable payload; may raise ModuleUnavailable
    render(data: dict) -> list[str]  payload -> body lines (no header, no indent)

Discovery uses only :mod:`importlib.metadata`, so loading plugins costs
zero extra dependencies — consistent with the project's few-dependencies
rule. Plugins always run *after* every built-in module, in entry-point
discovery order; they cannot reorder or replace a built-in.

Plugins are opt-in (``enable_plugins=True`` on :func:`blindsight.extract`,
``--enable-plugins`` on the CLI, ``BLINDSIGHT_ENABLE_PLUGINS=1`` for the MCP
server) rather than always-on. An installed plugin package runs arbitrary
third-party code the moment it is discovered, so a caller who never asked
for a plugin should never have one silently loaded and run against their
images.
"""

from __future__ import annotations

import warnings
from importlib.metadata import entry_points
from typing import Any, Iterable

ENTRY_POINT_GROUP = "blindsight.modules"

_REQUIRED_ATTRS = ("NAME", "TITLE", "run", "render")


class PluginLoadWarning(UserWarning):
    """A plugin entry point failed to load or violated the module contract."""


def _validation_error(obj: Any, ep_name: str) -> str | None:
    """Return a reason ``obj`` doesn't satisfy the module contract, or None."""
    missing = [attr for attr in _REQUIRED_ATTRS if not hasattr(obj, attr)]
    if missing:
        return f"plugin {ep_name!r} is missing {', '.join(missing)}"
    if not isinstance(obj.NAME, str) or not obj.NAME:
        return f"plugin {ep_name!r} has an invalid NAME"
    if not isinstance(obj.TITLE, str) or not obj.TITLE:
        return f"plugin {ep_name!r} has an invalid TITLE"
    if not callable(obj.run) or not callable(obj.render):
        return f"plugin {ep_name!r} has a non-callable run/render"
    return None


def discover(*, reserved_names: Iterable[str] = ()) -> list[Any]:
    """Load and validate every module registered under the entry-point group.

    A plugin that fails to import, doesn't match the module contract, or
    declares a ``NAME`` already claimed by a built-in module or an earlier
    plugin is skipped with a :class:`PluginLoadWarning` — one bad plugin
    package never breaks discovery of the others, the same
    graceful-degradation contract every built-in module follows for its
    own failures.

    Args:
        reserved_names: Names already taken (normally the built-in
            ``REGISTRY``'s ``NAME``s) that no plugin may reuse.

    Returns:
        Valid plugin modules, in entry-point discovery order.
    """
    seen = set(reserved_names)
    valid: list[Any] = []
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            obj = ep.load()
        except Exception as exc:
            warnings.warn(
                f"blindsight plugin {ep.name!r} failed to load: {exc}",
                PluginLoadWarning, stacklevel=2)
            continue
        error = _validation_error(obj, ep.name)
        if error:
            warnings.warn(error, PluginLoadWarning, stacklevel=2)
            continue
        if obj.NAME in seen:
            warnings.warn(
                f"blindsight plugin {ep.name!r} declares NAME={obj.NAME!r}, "
                "which is already registered — skipped",
                PluginLoadWarning, stacklevel=2)
            continue
        seen.add(obj.NAME)
        valid.append(obj)
    return valid
