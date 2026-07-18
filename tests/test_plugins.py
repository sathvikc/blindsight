"""Tests for the third-party plugin discovery mechanism.

Entry points are faked with lightweight stand-ins rather than an installed
package, so the suite needs no extra fixture package on the path.
"""

from __future__ import annotations

import warnings

import pytest
from PIL import Image

from blindsight import extract
from blindsight.modules import REGISTRY, load_registry
from blindsight.plugins import PluginLoadWarning, discover


class _FakeEntryPoint:
    def __init__(self, name, obj=None, error=None):
        self.name = name
        self._obj = obj
        self._error = error

    def load(self):
        if self._error is not None:
            raise self._error
        return self._obj


class _GoodPlugin:
    NAME = "fake_plugin"
    TITLE = "Fake Plugin"

    @staticmethod
    def run(ctx):
        return {"ok": True}

    @staticmethod
    def render(data):
        return [f"ok: {data['ok']}"]


class _MissingRenderPlugin:
    NAME = "broken_plugin"
    TITLE = "Broken Plugin"

    @staticmethod
    def run(ctx):
        return {}


def _patch_entry_points(monkeypatch, entry_points_list):
    def fake_entry_points(*, group):
        assert group == "blindsight.modules"
        return entry_points_list

    monkeypatch.setattr("blindsight.plugins.entry_points", fake_entry_points)


def test_discover_returns_empty_with_no_entry_points(monkeypatch):
    _patch_entry_points(monkeypatch, [])
    assert discover() == []


def test_discover_loads_a_valid_plugin(monkeypatch):
    _patch_entry_points(monkeypatch, [_FakeEntryPoint("good", _GoodPlugin)])
    found = discover()
    assert found == [_GoodPlugin]


def test_discover_skips_plugin_missing_required_attrs(monkeypatch):
    _patch_entry_points(
        monkeypatch, [_FakeEntryPoint("broken", _MissingRenderPlugin)])
    with pytest.warns(PluginLoadWarning, match="render"):
        found = discover()
    assert found == []


def test_discover_skips_plugin_that_fails_to_load(monkeypatch):
    _patch_entry_points(
        monkeypatch, [_FakeEntryPoint("explodes", error=ImportError("nope"))])
    with pytest.warns(PluginLoadWarning, match="failed to load"):
        found = discover()
    assert found == []


def test_discover_skips_name_collision_with_builtin(monkeypatch):
    class _ClashesWithStats:
        NAME = "stats"
        TITLE = "Clash"
        run = staticmethod(lambda ctx: {})
        render = staticmethod(lambda data: [])

    _patch_entry_points(
        monkeypatch, [_FakeEntryPoint("clash", _ClashesWithStats)])
    reserved = frozenset(m.NAME for m in REGISTRY)
    with pytest.warns(PluginLoadWarning, match="already registered"):
        found = discover(reserved_names=reserved)
    assert found == []


def test_discover_one_bad_plugin_does_not_block_a_good_one(monkeypatch):
    _patch_entry_points(monkeypatch, [
        _FakeEntryPoint("broken", _MissingRenderPlugin),
        _FakeEntryPoint("good", _GoodPlugin),
    ])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", PluginLoadWarning)
        found = discover()
    assert found == [_GoodPlugin]


def test_load_registry_without_plugins_is_unchanged():
    assert load_registry(enable_plugins=False) == list(REGISTRY)


def test_load_registry_appends_plugins_after_builtins(monkeypatch):
    _patch_entry_points(monkeypatch, [_FakeEntryPoint("good", _GoodPlugin)])
    registry = load_registry(enable_plugins=True)
    assert registry[:len(REGISTRY)] == list(REGISTRY)
    assert registry[len(REGISTRY):] == [_GoodPlugin]


def test_extract_runs_an_enabled_plugin(monkeypatch, tmp_path):
    _patch_entry_points(monkeypatch, [_FakeEntryPoint("good", _GoodPlugin)])
    path = tmp_path / "solid.png"
    Image.new("RGB", (40, 40), "white").save(path)

    descriptor = extract(str(path), enable_plugins=True)
    result = descriptor.get("fake_plugin")
    assert result is not None
    assert result.available
    assert result.data == {"ok": True}


def test_extract_ignores_plugins_by_default(monkeypatch, tmp_path):
    _patch_entry_points(monkeypatch, [_FakeEntryPoint("good", _GoodPlugin)])
    path = tmp_path / "solid.png"
    Image.new("RGB", (40, 40), "white").save(path)

    descriptor = extract(str(path))
    assert descriptor.get("fake_plugin") is None
