"""MCP server: the JSON-RPC surface a text-only model's client talks to.

Tests drive ``serve()`` end to end with real newline-delimited JSON-RPC frames — the same bytes an MCP client would send over stdio — rather than calling handlers directly, so framing, id handling, and notification semantics are all under test. Images are synthesized per test.
"""

from __future__ import annotations

import base64
import io
import json

import pytest
from PIL import Image, ImageDraw, ImageFont

from blindsight.modules import ocr
from blindsight import mcp_server


def _roundtrip(*messages: dict) -> list[dict]:
    """Feed JSON-RPC messages through serve() and decode the responses."""
    stdin = io.StringIO("".join(json.dumps(m) + "\n" for m in messages))
    stdout = io.StringIO()
    mcp_server.serve(stdin=stdin, stdout=stdout)
    return [json.loads(line) for line in stdout.getvalue().splitlines()]


def _call(msg_id: int, tool: str, arguments: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "method": "tools/call",
            "params": {"name": tool, "arguments": arguments}}


def _tesseract_available() -> bool:
    if ocr.pytesseract is None:
        return False
    try:
        ocr.pytesseract.get_tesseract_version()
    except Exception:
        return False
    return True


@pytest.fixture
def scene_path(tmp_path) -> str:
    """A simple scene: white page, blue rectangle, red circle."""
    img = Image.new("RGB", (400, 300), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, 180, 160], fill=(26, 60, 94))
    draw.ellipse([260, 180, 360, 280], fill="red")
    path = tmp_path / "scene.png"
    img.save(path)
    return str(path)


def test_initialize_reports_tools_capability():
    responses = _roundtrip({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18",
                   "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}},
    })
    result = responses[0]["result"]
    assert result["protocolVersion"] == "2025-06-18"
    assert "tools" in result["capabilities"]
    assert result["serverInfo"]["name"] == "blindsight"


def test_unknown_protocol_version_falls_back_to_newest():
    responses = _roundtrip({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "1999-01-01"},
    })
    assert responses[0]["result"]["protocolVersion"] == "2025-06-18"


def test_notifications_get_no_response():
    responses = _roundtrip(
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "ping"},
    )
    # Only the ping is answered; the notification is silently consumed.
    assert len(responses) == 1
    assert responses[0]["id"] == 2
    assert responses[0]["result"] == {}


def test_tools_list_exposes_all_four_tools():
    responses = _roundtrip(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    tools = responses[0]["result"]["tools"]
    names = {t["name"] for t in tools}
    assert names == {"describe_image", "read_text", "inspect_region",
                     "capabilities"}
    for tool in tools:
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"


def test_describe_image_from_path(scene_path):
    responses = _roundtrip(_call(1, "describe_image", {"source": scene_path}))
    result = responses[0]["result"]
    assert result.get("isError") is False
    text = result["content"][0]["text"]
    assert "=== IMAGE DESCRIPTOR ===" in text
    assert "[Colors]" in text
    assert "400x300" in text


def test_describe_image_from_base64(scene_path):
    with open(scene_path, "rb") as fh:
        payload = base64.b64encode(fh.read()).decode()
    responses = _roundtrip(_call(1, "describe_image", {"source": payload}))
    text = responses[0]["result"]["content"][0]["text"]
    assert "400x300" in text
    # The temp file the payload landed in must not leak into the output.
    assert "blindsight-" not in text
    assert "<base64 image>" in text


def test_describe_image_from_data_uri(scene_path):
    with open(scene_path, "rb") as fh:
        payload = base64.b64encode(fh.read()).decode()
    responses = _roundtrip(_call(
        1, "describe_image", {"source": f"data:image/png;base64,{payload}"}))
    assert "400x300" in responses[0]["result"]["content"][0]["text"]


def test_describe_image_json_format(scene_path):
    responses = _roundtrip(_call(
        1, "describe_image", {"source": scene_path, "format": "json"}))
    payload = json.loads(responses[0]["result"]["content"][0]["text"])
    assert payload["width"] == 400
    assert "colors" in payload["modules"]


def test_describe_image_module_subset(scene_path):
    responses = _roundtrip(_call(
        1, "describe_image",
        {"source": scene_path, "modules": ["stats", "colors"]}))
    text = responses[0]["result"]["content"][0]["text"]
    assert "[Stats]" in text
    assert "[Shapes]" not in text


def test_missing_file_is_tool_error_not_crash():
    responses = _roundtrip(
        _call(1, "describe_image", {"source": "/no/such/file.png"}),
        {"jsonrpc": "2.0", "id": 2, "method": "ping"},
    )
    result = responses[0]["result"]
    assert result["isError"] is True
    assert "not found" in result["content"][0]["text"]
    # The server survives to answer the next request.
    assert responses[1]["result"] == {}


def test_unknown_tool_is_jsonrpc_error():
    responses = _roundtrip(_call(1, "no_such_tool", {}))
    assert responses[0]["error"]["code"] == -32602


def test_unknown_method_is_jsonrpc_error():
    responses = _roundtrip(
        {"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}})
    assert responses[0]["error"]["code"] == -32601


def test_parse_error_is_reported_and_survivable():
    stdin = io.StringIO('this is not json\n'
                        '{"jsonrpc": "2.0", "id": 1, "method": "ping"}\n')
    stdout = io.StringIO()
    mcp_server.serve(stdin=stdin, stdout=stdout)
    responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert responses[0]["error"]["code"] == -32700
    assert responses[1]["result"] == {}


def test_inspect_region_zooms_into_the_crop(scene_path):
    # The red circle lives in the bottom-right quadrant; a crop there should
    # describe a mostly-red image.
    responses = _roundtrip(_call(
        1, "inspect_region",
        {"source": scene_path, "x0": 0.6, "y0": 0.55, "x1": 1.0, "y1": 1.0,
         "modules": ["colors"]}))
    result = responses[0]["result"]
    assert result.get("isError") is False
    text = result["content"][0]["text"]
    assert "region x=0.60-1.00" in text
    assert "red" in text.lower()


def test_inspect_region_rejects_bad_coordinates(scene_path):
    responses = _roundtrip(_call(
        1, "inspect_region",
        {"source": scene_path, "x0": 0.9, "y0": 0.1, "x1": 0.2, "y1": 0.5}))
    result = responses[0]["result"]
    assert result["isError"] is True
    assert "x0 < x1" in result["content"][0]["text"]


def test_capabilities_lists_every_module():
    responses = _roundtrip(_call(1, "capabilities", {}))
    text = responses[0]["result"]["content"][0]["text"]
    for name in ("stats", "ocr", "tables", "colors", "regions", "codes"):
        assert name in text


@pytest.mark.skipif(not _tesseract_available(), reason="tesseract not installed")
def test_read_text_reads_a_document(tmp_path):
    img = Image.new("L", (640, 320), 255)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    draw.text((40, 60), "QUARTERLY REPORT", fill=0, font=font)
    draw.text((40, 120), "REVENUE 1,234,567", fill=0, font=font)
    path = tmp_path / "doc.png"
    img.save(path)

    responses = _roundtrip(_call(
        1, "read_text", {"source": str(path), "include_positions": True}))
    text = responses[0]["result"]["content"][0]["text"]
    assert "QUARTERLY REPORT" in text
    assert "REVENUE" in text
    assert "line positions" in text


@pytest.mark.skipif(not _tesseract_available(), reason="tesseract not installed")
def test_zoom_loop_recovers_small_text(tmp_path):
    """The loop the server is designed around: overview misses tiny text,
    inspect_region at full resolution recovers it."""
    img = Image.new("L", (1200, 900), 255)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
    draw.text((980, 840), "SN-77An41-X", fill=120, font=font)
    path = tmp_path / "big.png"
    img.save(path)

    responses = _roundtrip(_call(
        1, "inspect_region",
        {"source": str(path), "x0": 0.75, "y0": 0.85, "x1": 1.0, "y1": 1.0,
         "modules": ["ocr"]}))
    text = responses[0]["result"]["content"][0]["text"]
    assert "SN-77An41-X" in text or "SN-77" in text
