#!/usr/bin/env python3
"""Render PDF pages to PNG. Optionally add a coordinate grid, overlay a region
manifest, build a contact sheet, or emit source-vs-extraction comparison sheets.

One contract: pixmap -> PNG, plus optional overlays. (This absorbs the former
`annotate_page_grid.py`.)

Examples:
    render_pdf.py sources/original.pdf work/source-render --contact-sheet
    render_pdf.py sources/original.pdf work/grid --pages 6 --grid 50
    render_pdf.py sources/original.pdf work/regions --regions assets/regions.json
    render_pdf.py sources/original.pdf work/regions --regions assets/regions.json \
        --region-compare
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont, ImageOps


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


def render_image(page: fitz.Page, dpi: int) -> Image.Image:
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def load_manifest(path: Path) -> tuple[Path, Path, list[dict]]:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    base = path.resolve().parent
    source = (base / cfg["source"]).resolve()
    out_dir = (base / cfg.get("output_dir", "../figures")).resolve()
    assets = cfg.get("assets", [])
    return source, out_dir, assets


def draw_grid(img: Image.Image, page: fitz.Page, dpi: int, step: int) -> None:
    scale = dpi / 72.0
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    for x_pt in range(0, int(page.rect.width) + 1, step):
        x = round(x_pt * scale)
        draw.line([(x, 0), (x, img.height)], fill=(255, 0, 0), width=1)
        draw.text((x + 2, 2), str(x_pt), fill=(180, 0, 0), font=font)
    for y_pt in range(0, int(page.rect.height) + 1, step):
        y = round(y_pt * scale)
        draw.line([(0, y), (img.width, y)], fill=(0, 80, 255), width=1)
        draw.text((2, y + 2), str(y_pt), fill=(0, 60, 180), font=font)


def draw_regions(img: Image.Image, page: fitz.Page, items: list[dict], dpi: int) -> None:
    scale = dpi / 72.0
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    for i, item in enumerate(items, 1):
        x0, y0, x1, y1 = (float(v) * scale for v in item["bbox"])
        draw.rectangle([x0, y0, x1, y1], outline=(0, 160, 0), width=2)
        tag = f"{i}. {item.get('output', '')}"
        tw = draw.textlength(tag, font=font)
        draw.rectangle([x0, max(0, y0 - 12), x0 + tw + 4, y0], fill=(0, 160, 0))
        draw.text((x0 + 2, max(0, y0 - 12)), tag, fill="white", font=font)


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


def side_by_side(asset_png: Image.Image, source_png: Image.Image, label: str) -> Image.Image:
    width = max(asset_png.width, source_png.width)
    gap, header = 12, 22

    def fit(im: Image.Image) -> Image.Image:
        if im.width == width:
            return im
        return im.resize((width, max(1, round(im.height * width / im.width))))

    left, right = fit(asset_png), fit(source_png)
    canvas = Image.new("RGB", (width * 2 + gap, max(left.height, right.height) + header), "white")
    d = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    d.text((4, 4), f"{label}  |  left = extracted asset, right = source region", fill="black", font=font)
    canvas.paste(left, (0, header))
    canvas.paste(right, (width + gap, header))
    d.line([(width + gap // 2, header), (width + gap // 2, canvas.height)], fill="black", width=1)
    return canvas


def emit_region_comparisons(source: Path, out_dir: Path, assets: list[dict], target: Path, dpi: int) -> int:
    src_doc = fitz.open(source)
    made = 0
    target.mkdir(parents=True, exist_ok=True)
    try:
        for i, item in enumerate(assets, 1):
            name = item.get("output", f"asset{i}.pdf")
            if not name.lower().endswith(".pdf"):
                name += ".pdf"
            asset_path = out_dir / name
            if not asset_path.is_file():
                print(f"  ! missing extracted asset {asset_path}; run extract_vector_regions.py first")
                continue
            page_no = int(item["page"])
            rect = fitz.Rect(*map(float, item["bbox"]))
            src_pix = src_doc[page_no - 1].get_pixmap(
                matrix=fitz.Matrix(dpi / 72, dpi / 72), clip=rect, alpha=False)
            src_img = Image.frombytes("RGB", [src_pix.width, src_pix.height], src_pix.samples)
            with fitz.open(asset_path) as adoc:
                asset_img = render_image(adoc[0], dpi)
            side_by_side(asset_img, src_img, f"{i}. {name} (p.{page_no})").save(target / f"compare-{i:02d}-{Path(name).stem}.png")
            made += 1
    finally:
        src_doc.close()
    return made


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--dpi", type=int, default=180)
    ap.add_argument("--pages", help="1-based list/ranges, e.g. 1-3,7,10")
    ap.add_argument("--contact-sheet", action="store_true")
    ap.add_argument("--columns", type=int, default=4)
    ap.add_argument("--grid", type=int, metavar="STEP", help="overlay a PDF-point grid every STEP points")
    ap.add_argument("--regions", type=Path, help="overlay assets/regions.json boxes on the source pages")
    ap.add_argument("--region-compare", action="store_true",
                    help="with --regions: emit extracted-asset vs source-region sheets")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    selected = parse_pages(args.pages, len(doc))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    by_page: dict[int, list[dict]] = {}
    if args.regions:
        man_source, man_out, assets = load_manifest(args.regions)
        if man_source.exists() and man_source.resolve() != args.pdf.resolve():
            print(f"warning: manifest source ({man_source.name}) differs from rendered PDF ({args.pdf.name})")
        for item in assets:
            by_page.setdefault(int(item["page"]), []).append(item)

    for pno in selected:
        page = doc[pno]
        img = render_image(page, args.dpi)
        path = args.out_dir / f"page-{pno + 1:03d}.png"
        img.save(path)
        outputs.append(path)
        if args.grid:
            grid_img = img.copy()
            draw_grid(grid_img, page, args.dpi, args.grid)
            grid_img.save(args.out_dir / f"grid-page-{pno + 1:03d}.png")
        if args.regions and pno + 1 in by_page:
            reg_img = img.copy()
            draw_regions(reg_img, page, by_page[pno + 1], args.dpi)
            reg_img.save(args.out_dir / f"regions-page-{pno + 1:03d}.png")
    page_size = doc[0].rect if len(doc) else None
    doc.close()

    if args.contact_sheet:
        contact = args.out_dir / "contact-sheet.png"
        make_contact_sheet(outputs, contact, columns=args.columns)
        print(f"Contact sheet: {contact}")
    if args.regions and args.region_compare:
        made = emit_region_comparisons(man_source, man_out, assets, args.out_dir / "region-compare", args.dpi)
        print(f"Region comparison sheets: {made} -> {args.out_dir / 'region-compare'}")
    print(f"Rendered {len(outputs)} pages -> {args.out_dir}")
    if page_size is not None:
        print(f"Page size: {page_size.width:.2f} x {page_size.height:.2f} pt")


if __name__ == "__main__":
    main()
