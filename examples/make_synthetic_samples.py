#!/usr/bin/env python3
"""Generate the synthetic showcase images (receipt, QR, barcode, chart, UI, logo).

These are deterministic so the showcase can be regenerated at any time. Run:

    python examples/make_synthetic_samples.py

Real photographs in examples/images/ are downloaded separately, not produced here.
"""

from __future__ import annotations

from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "images"
OUT.mkdir(parents=True, exist_ok=True)

MONO = "/System/Library/Fonts/Menlo.ttc"
SANS = "/System/Library/Fonts/Supplemental/Arial.ttf"
SANS_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def receipt() -> None:
    img = Image.new("RGB", (420, 560), "white")
    d = ImageDraw.Draw(img)
    f = font(MONO, 18)
    fb = font(MONO, 22)
    lines = [
        ("       BLUE CART MARKET", fb),
        ("    123 Banjara Hills, Hyd", f),
        ("-" * 30, f),
        ("Date: 2026-05-12  14:32", f),
        ("Receipt #: 004871", f),
        ("-" * 30, f),
        ("Milk 1L            x2   90.00", f),
        ("Brown Bread        x1   45.00", f),
        ("Eggs (12)          x1  120.00", f),
        ("Bananas 1kg        x1   60.00", f),
        ("Coffee 200g        x1  340.00", f),
        ("-" * 30, f),
        ("SUBTOTAL              655.00", f),
        ("GST 5%                 32.75", f),
        ("TOTAL              Rs 687.75", fb),
        ("-" * 30, f),
        ("   THANK YOU FOR SHOPPING", f),
    ]
    y = 24
    for text, fnt in lines:
        d.text((20, y), text, fill=(20, 20, 20), font=fnt)
        y += 30
    img.save(OUT / "receipt.png")


def qr_code() -> None:
    img = qrcode.make("https://sathvikc.github.io/lume-js/").convert("RGB")
    img = img.resize((360, 360), Image.NEAREST)
    img.save(OUT / "qr_code.png")


def barcode_img() -> None:
    from barcode import EAN13
    from barcode.writer import ImageWriter

    ean = EAN13("590123412345", writer=ImageWriter())
    ean.save(str(OUT / "barcode"))  # writes barcode.png


def bar_chart() -> None:
    img = Image.new("RGB", (640, 420), "white")
    d = ImageDraw.Draw(img)
    title = font(SANS_B, 24)
    label = font(SANS, 16)

    d.text((150, 16), "Quarterly Revenue (Cr)", fill=(20, 20, 20), font=title)
    # axes
    x0, y0, x1, y1 = 70, 360, 600, 360
    d.line([x0, 60, x0, y0], fill=(0, 0, 0), width=2)       # y axis
    d.line([x0, y0, x1, y1], fill=(0, 0, 0), width=2)       # x axis

    bars = [("Q1", 120, (31, 119, 180)), ("Q2", 200, (255, 127, 14)),
            ("Q3", 160, (44, 160, 44)), ("Q4", 280, (214, 39, 40))]
    bw = 90
    gap = 40
    x = x0 + gap
    for name, value, color in bars:
        top = y0 - value
        d.rectangle([x, top, x + bw, y0], fill=color)
        d.text((x + 28, y0 + 8), name, fill=(20, 20, 20), font=label)
        d.text((x + 22, top - 22), str(value), fill=(20, 20, 20), font=label)
        x += bw + gap
    img.save(OUT / "bar_chart.png")


def app_ui() -> None:
    img = Image.new("RGB", (390, 700), (245, 246, 248))
    d = ImageDraw.Draw(img)
    hd = font(SANS_B, 26)
    rw = font(SANS, 20)
    btn = font(SANS_B, 22)

    d.rectangle([0, 0, 390, 90], fill=(33, 99, 232))          # header
    d.text((24, 36), "Settings", fill="white", font=hd)

    rows = ["Account", "Notifications", "Privacy", "Appearance", "Storage"]
    y = 120
    for r in rows:
        d.rectangle([16, y, 374, y + 64], fill="white", outline=(225, 228, 232))
        d.text((28, y + 20), r, fill=(30, 30, 30), font=rw)
        d.ellipse([320, y + 20, 356, y + 44],
                  fill=(76, 200, 120) if r != "Privacy" else (200, 205, 210))
        y += 80

    d.rounded_rectangle([40, 600, 350, 656], radius=14, fill=(33, 99, 232))
    d.text((150, 614), "Save", fill="white", font=btn)
    img.save(OUT / "app_ui.png")


def logo() -> None:
    img = Image.new("RGB", (480, 360), "white")
    d = ImageDraw.Draw(img)
    cx, cy, r = 160, 150, 90
    hexagon = [(cx + r * __import__("math").cos(a),
                cy + r * __import__("math").sin(a))
               for a in [i * 3.14159 / 3 for i in range(6)]]
    d.polygon(hexagon, fill=(33, 99, 232))
    d.polygon([(130, 120), (210, 120), (170, 195)], fill="white")  # inner triangle
    d.text((270, 120), "NOVA", fill=(20, 20, 20),
           font=font(SANS_B, 56))
    img.save(OUT / "logo.png")


def main() -> None:
    receipt()
    qr_code()
    barcode_img()
    bar_chart()
    app_ui()
    logo()
    print(f"generated synthetic samples in {OUT}/")
    # Note: blindsight_logo.png is the project's real brand mark (a committed
    # asset), not a generated sample, so it is intentionally not produced here.


if __name__ == "__main__":
    main()
