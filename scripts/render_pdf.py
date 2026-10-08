#!/usr/bin/env python3
"""Render PDF pages to PNG and optionally create a contact sheet."""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import fitz
from PIL import Image, ImageOps, ImageDraw


def parse_pages(spec: str | None, n_pages: int) -> list[int]:
    if not spec:
        return list(range(n_pages))
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
            if start > end:
                start, end = end, start
            out.update(range(start - 1, end))
        else:
            out.add(int(part) - 1)
    bad = [p + 1 for p in out if p < 0 or p >= n_pages]
    if bad:
        raise ValueError(f"Page numbers out of range: {bad}")
    return sorted(out)


def render_page(page: fitz.Page, dpi: int, out_path: Path) -> None:
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    pix.save(out_path)


def make_contact_sheet(paths: list[Path], output: Path, thumb_width: int = 300, columns: int = 4) -> None:
    thumbs = []
    for p in paths:
        img = Image.open(p).convert("RGB")
        scale = thumb_width / img.width
        size = (thumb_width, max(1, int(img.height * scale)))
        thumb = img.resize(size)
        thumb = ImageOps.expand(thumb, border=1, fill="black")
        canvas = Image.new("RGB", (thumb.width, thumb.height + 26), "white")
        canvas.paste(thumb, (0, 26))
        d = ImageDraw.Draw(canvas)
        d.text((6, 6), p.stem, fill="black")
        thumbs.append(canvas)

    if not thumbs:
        return
    rows = math.ceil(len(thumbs) / columns)
    cell_w = max(t.width for t in thumbs)
    cell_h = max(t.height for t in thumbs)
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), "white")
    for i, t in enumerate(thumbs):
        x = (i % columns) * cell_w
        y = (i // columns) * cell_h
        sheet.paste(t, (x, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--dpi", type=int, default=180)
    ap.add_argument("--pages", help="1-based list/ranges, e.g. 1-3,7,10")
    ap.add_argument("--contact-sheet", action="store_true")
    ap.add_argument("--columns", type=int, default=4)
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    selected = parse_pages(args.pages, len(doc))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for pno in selected:
        path = args.out_dir / f"page-{pno + 1:03d}.png"
        render_page(doc[pno], args.dpi, path)
        outputs.append(path)
    doc.close()

    if args.contact_sheet:
        contact = args.out_dir / "contact-sheet.png"
        make_contact_sheet(outputs, contact, columns=args.columns)
        print(f"Contact sheet: {contact}")
    print(f"Rendered {len(outputs)} pages -> {args.out_dir}")


if __name__ == "__main__":
    main()
