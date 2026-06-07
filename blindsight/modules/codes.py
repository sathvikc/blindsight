"""QR code and barcode decoding.

Uses OpenCV's built-in ``QRCodeDetector`` so no extra system library (such as
zbar) is required. Linear barcodes are decoded too when the installed OpenCV
build ships the optional ``barcode`` module; otherwise only QR codes are read.
"""

from __future__ import annotations

from typing import Any

from ..context import ImageContext, ModuleUnavailable

NAME = "codes"
TITLE = "Codes"

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


def _decode_qr(bgr) -> list[dict[str, str]]:
    detector = cv2.QRCodeDetector()
    found: list[dict[str, str]] = []
    # Return arity of these calls varies across OpenCV versions, so unpack
    # positionally rather than assuming a fixed tuple length.
    try:
        result = detector.detectAndDecodeMulti(bgr)
        ok, decoded = result[0], result[1]
        if ok:
            for value in decoded:
                if value:
                    found.append({"type": "QR", "value": value})
    except (cv2.error, IndexError):
        try:
            value = detector.detectAndDecode(bgr)[0]
            if value:
                found.append({"type": "QR", "value": value})
        except (cv2.error, IndexError):
            pass
    return found


def _decode_barcodes(bgr) -> list[dict[str, str]]:
    if not hasattr(cv2, "barcode"):
        return []
    detector = cv2.barcode.BarcodeDetector()
    try:
        result = detector.detectAndDecode(bgr)
    except (cv2.error, IndexError):
        return []
    # 4-tuple (ok, info, types, points) on some builds; 3-tuple (info, types,
    # points) on others. Normalise to the decoded-info and type sequences.
    if len(result) == 4:
        decoded, types = result[1], result[2]
    elif len(result) == 3:
        decoded, types = result[0], result[1]
    else:
        return []
    if not decoded:
        return []
    found: list[dict[str, str]] = []
    for value, btype in zip(decoded, types or [""] * len(decoded)):
        if value:
            found.append({"type": str(btype) or "barcode", "value": value})
    return found


def run(ctx: ImageContext) -> dict[str, Any]:
    if cv2 is None:
        raise ModuleUnavailable("opencv-python is not installed")

    bgr = ctx.bgr.copy()  # OpenCV detectors expect a contiguous array
    codes = _decode_qr(bgr)
    try:
        codes += _decode_barcodes(bgr)
    except Exception:
        pass  # linear-barcode support is best-effort; never lose a QR result
    return {"count": len(codes), "codes": codes}


def render(data: dict[str, Any]) -> list[str]:
    if data["count"] == 0:
        return ["none"]
    return [f"{c['type']}: {c['value']}" for c in data["codes"]]
