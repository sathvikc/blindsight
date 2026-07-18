"""MCP server: give any text-only model the ability to "see" images.

Exposes Blindsight over the Model Context Protocol so models with no vision input at all — DeepSeek, cheap text endpoints, local models — can ask factual questions about images. The client sends a file path, URL, or base64 image; the model gets back the compact text descriptor instead of pixels.

The server speaks MCP's stdio transport directly: newline-delimited JSON-RPC 2.0 on stdin/stdout. That subset of the protocol (initialize, ping, tools/list, tools/call) is small and stable, so implementing it here keeps the project's zero-extra-dependencies rule — no SDK required, the standard library is enough. Run it with::

    python -m blindsight.mcp_server        # or the blindsight-mcp script

Four tools, designed as a loop rather than a single shot:

- ``describe_image`` — the full descriptor: the first call for any image. - ``read_text`` — OCR + tables in a document-shaped rendering, for dense text images (receipts, invoices, screenshots of documents). - ``inspect_region`` — re-run extraction on one region of the image. The crop is taken from the full-resolution original, so small text that was unreadable in the overview usually resolves on the second, zoomed look. - ``capabilities`` — what is installed and how to use the loop.

Everything the descriptor honestly cannot answer (mood, scene meaning, identity) stays unanswered — the tool descriptions say so, so the model knows to tell its user a real vision model is needed.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import sys
import tempfile
import urllib.request
from typing import Any

from . import __version__
from .extractor import extract
from .modules import load_registry

# Protocol revisions this server implements. The tools-only subset is
# identical across them, so we accept any of these and echo it back;
# anything unknown gets the newest we know.
_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")

_MAX_DOWNLOAD = 30 * 1024 * 1024  # refuse image downloads larger than this
_FETCH_TIMEOUT = 30               # seconds

# Plugins run arbitrary third-party code, so — like the CLI's
# --enable-plugins — they are opt-in, here via an env var set before the
# server starts (there's no argv the MCP client lets you pass through).
_ENABLE_PLUGINS = os.environ.get("BLINDSIGHT_ENABLE_PLUGINS", "").strip().lower() in (
    "1", "true", "yes", "on")
_REGISTRY = load_registry(enable_plugins=_ENABLE_PLUGINS)
_MODULE_NAMES = [m.NAME for m in _REGISTRY]

_SOURCE_DESC = (
    "The image: a local file path, an http(s) URL, a data: URI, or a bare "
    "base64-encoded image."
)

# Fractions of image width/height, so callers never need pixel dimensions.
_REGION_PROPS = {
    "x0": {"type": "number", "minimum": 0, "maximum": 1,
           "description": "Left edge of the region, 0.0-1.0."},
    "y0": {"type": "number", "minimum": 0, "maximum": 1,
           "description": "Top edge of the region, 0.0-1.0."},
    "x1": {"type": "number", "minimum": 0, "maximum": 1,
           "description": "Right edge of the region, 0.0-1.0."},
    "y1": {"type": "number", "minimum": 0, "maximum": 1,
           "description": "Bottom edge of the region, 0.0-1.0."},
}

_TOOLS: list[dict[str, Any]] = [
    {
        "name": "describe_image",
        "description": (
            "Extract a factual text descriptor from an image using classical "
            "image processing (no vision model): resolution, OCR text with "
            "layout, ruled tables as rows of cells, colours, region "
            "geometry, shapes, faces count, QR/barcode values, EXIF. Call "
            "this first for any image. The descriptor reports measured facts "
            "only — if the question is perceptual (mood, scene meaning, who "
            "a person is), the descriptor cannot answer it and a real vision "
            "model is needed; say so rather than guessing. If text comes "
            "back low-confidence or truncated, follow up with inspect_region "
            "on the area of interest."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": _SOURCE_DESC},
                "modules": {
                    "type": "array",
                    "items": {"type": "string", "enum": _MODULE_NAMES},
                    "description": ("Optional subset of modules to run "
                                    "(default: all of them)."),
                },
                "format": {
                    "type": "string",
                    "enum": ["text", "json"],
                    "description": ("'text' (default) is the compact "
                                    "LLM-friendly block; 'json' carries the "
                                    "same data with exact coordinates."),
                },
            },
            "required": ["source"],
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "read_text",
        "description": (
            "Deep-read a text-heavy image (receipt, invoice, document scan, "
            "screenshot, slide): full OCR in reading order with paragraph "
            "breaks, plus any ruled tables reconstructed cell by cell. "
            "Handles tilted scans and light-on-dark text. Use this instead "
            "of describe_image when you only care about what the image says. "
            "Set include_positions=true to get each line's bounding box for "
            "follow-up inspect_region calls."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": _SOURCE_DESC},
                "include_positions": {
                    "type": "boolean",
                    "description": ("Also list each text line's relative "
                                    "bounding box (default false)."),
                },
            },
            "required": ["source"],
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "inspect_region",
        "description": (
            "Zoom into one region of the image and re-run extraction on just "
            "that crop, at full original resolution. Use it when the "
            "overview descriptor flags something worth a closer look: "
            "low-confidence OCR, a small region, an unreadable code. "
            "Coordinates are fractions of the image (0,0 is top-left; the "
            "whole image is 0,0,1,1), matching the positions the other tools "
            "report."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": _SOURCE_DESC},
                **_REGION_PROPS,
                "modules": {
                    "type": "array",
                    "items": {"type": "string", "enum": _MODULE_NAMES},
                    "description": ("Optional subset of modules to run on "
                                    "the crop (default: all)."),
                },
            },
            "required": ["source", "x0", "y0", "x1", "y1"],
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "capabilities",
        "description": (
            "Report which extraction modules are available in this "
            "installation (OCR needs the Tesseract binary) and how the tools "
            "are meant to be combined. Call once per session if a module "
            "keeps coming back unavailable."
        ),
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True},
    },
]


# ---------------------------------------------------------------------------
# Image source handling


class SourceError(Exception):
    """The image argument could not be turned into a readable local file."""


def _fetch_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "blindsight-mcp"})
    with urllib.request.urlopen(request, timeout=_FETCH_TIMEOUT) as resp:
        length = resp.headers.get("Content-Length")
        if length and int(length) > _MAX_DOWNLOAD:
            raise SourceError(f"image at {url} exceeds {_MAX_DOWNLOAD} bytes")
        data = resp.read(_MAX_DOWNLOAD + 1)
    if len(data) > _MAX_DOWNLOAD:
        raise SourceError(f"image at {url} exceeds {_MAX_DOWNLOAD} bytes")
    return data


def _decode_base64(payload: str) -> bytes:
    try:
        return base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SourceError(f"invalid base64 image data: {exc}") from exc


def _source_bytes(source: str) -> tuple[bytes | None, str]:
    """Resolve a source argument to (raw bytes, display label).

    ``None`` bytes means the source is already a local path and can be read in place. Everything else — URL, data URI, bare base64 — is materialised to bytes for a temp file.
    """
    if source.startswith("data:"):
        _head, _sep, payload = source.partition(",")
        if not _sep:
            raise SourceError("malformed data: URI (no comma)")
        return _decode_base64(payload.strip()), "<data URI>"
    if source.startswith(("http://", "https://")):
        return _fetch_url(source), source
    if os.path.exists(source):
        return None, source
    # Not a path, not a URL: last interpretation is bare base64. Whitespace
    # is stripped because clients often wrap long payloads.
    compact = "".join(source.split())
    if len(compact) > 64:
        try:
            return _decode_base64(compact), "<base64 image>"
        except SourceError:
            pass
    raise SourceError(
        f"image not found: {source!r} is not an existing file, a URL, "
        "a data: URI, or valid base64")


def _extract_from_source(source: str, modules: list[str] | None = None,
                         crop: tuple[float, float, float, float] | None = None):
    """Load a source, optionally crop it, and run extraction.

    Returns the descriptor with ``source`` rewritten to the display label so temp-file paths never leak into the output the model reads.
    """
    data, label = _source_bytes(source)

    tmp_path: str | None = None
    try:
        path = source
        if data is not None:
            fd, tmp_path = tempfile.mkstemp(prefix="blindsight-", suffix=".img")
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            path = tmp_path

        if crop is not None:
            from PIL import Image

            x0, y0, x1, y1 = crop
            with Image.open(path) as img:
                img.load()
                w, h = img.size
                box = (round(x0 * w), round(y0 * h),
                       round(x1 * w), round(y1 * h))
                if box[2] - box[0] < 4 or box[3] - box[1] < 4:
                    raise SourceError(
                        f"region {crop} is smaller than 4x4 pixels of this "
                        f"{w}x{h} image — widen it")
                region = img.convert("RGB").crop(box)
            fd, crop_path = tempfile.mkstemp(prefix="blindsight-crop-",
                                             suffix=".png")
            os.close(fd)
            region.save(crop_path)
            if tmp_path is not None:
                os.unlink(tmp_path)
            tmp_path, path = crop_path, crop_path
            label = (f"{label} [region x={x0:.2f}-{x1:.2f}, "
                     f"y={y0:.2f}-{y1:.2f}]")

        descriptor = extract(path, modules=modules, enable_plugins=_ENABLE_PLUGINS)
        descriptor.source = label
        return descriptor
    finally:
        if tmp_path is not None and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Tool implementations (each returns the text the model will read)


def _validate_modules(modules: Any) -> list[str] | None:
    if modules is None:
        return None
    unknown = [m for m in modules if m not in _MODULE_NAMES]
    if unknown:
        raise SourceError(
            f"unknown module(s): {', '.join(unknown)} — "
            f"available: {', '.join(_MODULE_NAMES)}")
    return list(modules)


def _tool_describe_image(args: dict[str, Any]) -> str:
    modules = _validate_modules(args.get("modules"))
    descriptor = _extract_from_source(args["source"], modules=modules)
    if args.get("format") == "json":
        return json.dumps(descriptor.to_json(), indent=2)
    return descriptor.to_text()


def _tool_read_text(args: dict[str, Any]) -> str:
    descriptor = _extract_from_source(args["source"],
                                      modules=["ocr", "tables"])
    ocr = descriptor.get("ocr")
    tables = descriptor.get("tables")

    lines: list[str] = [f"source: {descriptor.source}",
                        f"size: {descriptor.width}x{descriptor.height}", ""]

    if ocr is None or not ocr.available:
        note = ocr.note if ocr is not None else "module missing"
        lines.append(f"OCR unavailable: {note}")
    elif ocr.data["word_count"] == 0:
        lines.append("No text detected.")
    else:
        conf = ocr.data["confidence"]
        reliability = "reliable" if conf >= 75 else "uncertain"
        recovered = ocr.data.get("pass")
        suffix = (f", recovered via {recovered} pass"
                  if recovered not in (None, "original", "binarized") else "")
        lines.append(f"confidence: {conf}% ({reliability}{suffix})")
        lines.append("")
        for para in ocr.data["paragraphs"]:
            lines.extend(para)
            lines.append("")

    if tables is not None and tables.available and tables.data["count"]:
        lines.append("--- tables (cells in reading order) ---")
        lines.extend(tables.render(tables.data))
        lines.append("")

    if (ocr is not None and ocr.available and ocr.data["word_count"]
            and args.get("include_positions")):
        lines.append("--- line positions (fractions of image) ---")
        for box in ocr.data["line_boxes"]:
            lines.append(
                f'({box["x0"]:.2f},{box["y0"]:.2f})-'
                f'({box["x1"]:.2f},{box["y1"]:.2f}) "{box["text"]}"')

    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _tool_inspect_region(args: dict[str, Any]) -> str:
    coords = []
    for key in ("x0", "y0", "x1", "y1"):
        value = args[key]
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise SourceError(f"{key} must be a number between 0 and 1")
        coords.append(float(value))
    x0, y0, x1, y1 = coords
    if x1 <= x0 or y1 <= y0:
        raise SourceError("region is empty: need x0 < x1 and y0 < y1")
    modules = _validate_modules(args.get("modules"))
    descriptor = _extract_from_source(args["source"], modules=modules,
                                      crop=(x0, y0, x1, y1))
    return descriptor.to_text()


_BUILTIN_NAMES = frozenset(m.NAME for m in load_registry(enable_plugins=False))


def _probe_module(module) -> tuple[bool, str]:
    if module.NAME == "ocr":
        try:
            import pytesseract
            version = pytesseract.get_tesseract_version()
            return True, f"tesseract {version}"
        except Exception as exc:
            return False, f"needs the tesseract binary ({exc})"
    if module.NAME not in _BUILTIN_NAMES:
        # Third-party plugin: no built-in probe knows its dependencies, so
        # report it loaded rather than guessing at an unrelated one (cv2).
        return True, "plugin, loaded"
    try:
        import cv2  # noqa: F401 - probing the import is the point
    except ImportError:
        return False, "needs opencv-python"
    return True, "ready"


def _tool_capabilities(_args: dict[str, Any]) -> str:
    lines = [f"blindsight {__version__} — classical image analysis, no vision model",
             "", f"plugins: {'enabled' if _ENABLE_PLUGINS else 'disabled (set BLINDSIGHT_ENABLE_PLUGINS=1 to load third-party modules)'}",
             "", "modules:"]
    for module in _REGISTRY:
        ok, note = _probe_module(module)
        status = "available" if ok else "UNAVAILABLE"
        lines.append(f"  {module.NAME:<10} {status:<12} {note}")
    lines += [
        "",
        "suggested loop:",
        "  1. describe_image for the overview (or read_text for documents)",
        "  2. inspect_region to zoom where OCR was uncertain or detail is small",
        "  3. if the question is perceptual (mood, identity, scene meaning),",
        "     the descriptor cannot answer it — recommend a vision model",
    ]
    return "\n".join(lines)


_TOOL_HANDLERS = {
    "describe_image": _tool_describe_image,
    "read_text": _tool_read_text,
    "inspect_region": _tool_inspect_region,
    "capabilities": _tool_capabilities,
}


# ---------------------------------------------------------------------------
# JSON-RPC plumbing


def _result(msg_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id,
            "error": {"code": code, "message": message}}


def _tool_text(text: str, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _handle_initialize(params: dict[str, Any]) -> dict[str, Any]:
    requested = params.get("protocolVersion")
    version = requested if requested in _PROTOCOL_VERSIONS else _PROTOCOL_VERSIONS[0]
    return {
        "protocolVersion": version,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "blindsight", "version": __version__},
        "instructions": (
            "Blindsight turns images into factual text descriptors with "
            "classical image processing, so a text-only model can answer "
            "questions about them. Start with describe_image (or read_text "
            "for documents), then inspect_region to zoom into anything "
            "uncertain. It measures; it does not interpret — perceptual "
            "questions still need a vision model."
        ),
    }


def _handle_tools_call(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        raise KeyError(name)
    args = params.get("arguments") or {}
    try:
        return _tool_text(handler(args))
    except SourceError as exc:
        return _tool_text(f"error: {exc}", is_error=True)
    except KeyError as exc:
        return _tool_text(f"error: missing required argument {exc}",
                          is_error=True)
    except Exception as exc:  # defensive: a bad image must not kill the server
        return _tool_text(f"error: could not process image: {exc}",
                          is_error=True)


def handle_message(message: Any) -> dict[str, Any] | None:
    """Handle one decoded JSON-RPC message; ``None`` means nothing to send."""
    if not isinstance(message, dict):
        return _error(None, -32600, "invalid request")

    method = message.get("method")
    msg_id = message.get("id")
    is_notification = "id" not in message
    params = message.get("params") or {}

    try:
        if method == "initialize":
            return _result(msg_id, _handle_initialize(params))
        if method == "ping":
            return _result(msg_id, {})
        if method == "tools/list":
            return _result(msg_id, {"tools": _TOOLS})
        if method == "tools/call":
            try:
                return _result(msg_id, _handle_tools_call(params))
            except KeyError as exc:
                return _error(msg_id, -32602, f"unknown tool: {exc}")
        if method and method.startswith("notifications/"):
            return None
        if is_notification:
            return None
        return _error(msg_id, -32601, f"method not found: {method}")
    except Exception as exc:  # pragma: no cover - last-resort guard
        if is_notification:
            return None
        return _error(msg_id, -32603, f"internal error: {exc}")


def serve(stdin=None, stdout=None) -> int:
    """Run the newline-delimited JSON-RPC loop until stdin closes."""
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout

    def send(payload: dict[str, Any]) -> None:
        stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        stdout.flush()

    for raw in stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            message = json.loads(raw)
        except json.JSONDecodeError as exc:
            send(_error(None, -32700, f"parse error: {exc}"))
            continue
        # A JSON-RPC batch is a list; MCP clients don't usually send them,
        # but answering each entry is cheap and correct for the ones that do.
        for msg in message if isinstance(message, list) else [message]:
            response = handle_message(msg)
            if response is not None:
                send(response)
    return 0


def main() -> int:
    try:
        return serve()
    except KeyboardInterrupt:  # pragma: no cover - clean Ctrl-C exit
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
