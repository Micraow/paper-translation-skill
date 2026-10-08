#!/usr/bin/env python3
"""Render one PDF page with a PDF-point coordinate grid for crop selection."""
from __future__ import annotations

import argparse
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("page", type=int, help="1-based page number")
    ap.add_argument("output", type=Path)
    ap.add_argument("--dpi", type=int, default=180)
    ap.add_argument("--step", type=int, default=50, help="grid step in PDF points")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    if args.page < 1 or args.page > len(doc):
        raise SystemExit(f"Page must be between 1 and {len(doc)}")
    page = doc[args.page - 1]
    scale = args.dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    for x_pt in range(0, int(page.rect.width) + 1, args.step):
        x = round(x_pt * scale)
        draw.line([(x, 0), (x, img.height)], fill=(255, 0, 0), width=1)
        draw.text((x + 2, 2), str(x_pt), fill=(180, 0, 0), font=font)
    for y_pt in range(0, int(page.rect.height) + 1, args.step):
        y = round(y_pt * scale)
        draw.line([(0, y), (img.width, y)], fill=(0, 80, 255), width=1)
        draw.text((2, y + 2), str(y_pt), fill=(0, 60, 180), font=font)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    img.save(args.output)
    width_pt, height_pt = page.rect.width, page.rect.height
    doc.close()
    print(f"Page size: {width_pt:.2f} x {height_pt:.2f} pt")
    print(f"Wrote grid: {args.output}")


if __name__ == "__main__":
    main()
