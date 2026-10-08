#!/usr/bin/env python3
"""Inspect a PDF for page geometry, text, images, drawings, fonts, and links.

Use this before deciding whether visible figures can be extracted as raster images
or should instead be preserved with vector PDF crops.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz


def page_record(doc: fitz.Document, pno: int) -> dict:
    page = doc[pno]
    images = page.get_images(full=True)
    drawings = page.get_drawings()
    links = page.get_links()
    fonts = page.get_fonts(full=True)
    text = page.get_text("text")

    image_records = []
    seen = set()
    for img in images:
        xref = int(img[0])
        if xref in seen:
            continue
        seen.add(xref)
        info = {
            "xref": xref,
            "width": int(img[2]),
            "height": int(img[3]),
            "bpc": int(img[4]),
            "colorspace": str(img[5]),
            "name": str(img[7]),
        }
        image_records.append(info)

    font_records = []
    for f in fonts:
        # PyMuPDF tuple shape can grow across versions; first six fields are stable.
        font_records.append({
            "xref": int(f[0]),
            "ext": str(f[1]),
            "type": str(f[2]),
            "basefont": str(f[3]),
            "name": str(f[4]),
            "encoding": str(f[5]),
        })

    return {
        "page": pno + 1,
        "width_pt": round(page.rect.width, 2),
        "height_pt": round(page.rect.height, 2),
        "text_chars": len(text),
        "embedded_images": image_records,
        "drawing_objects": len(drawings),
        "fonts": font_records,
        "links": len(links),
        "goto_links": sum(1 for x in links if x.get("kind") == fitz.LINK_GOTO),
        "uri_links": sum(1 for x in links if x.get("kind") == fitz.LINK_URI),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    records = [page_record(doc, i) for i in range(len(doc))]
    summary = {
        "file": str(args.pdf),
        "pages": len(doc),
        "metadata": doc.metadata,
        "page_records": records,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"PDF: {args.pdf}")
        print(f"Pages: {len(doc)}")
        total_goto = 0
        total_uri = 0
        for r in records:
            total_goto += r["goto_links"]
            total_uri += r["uri_links"]
            print(
                f"p{r['page']:03d} {r['width_pt']}x{r['height_pt']}pt | "
                f"text={r['text_chars']:5d} | images={len(r['embedded_images']):2d} | "
                f"drawings={r['drawing_objects']:4d} | links={r['links']:3d}"
            )
            for img in r["embedded_images"]:
                print(
                    f"    image xref={img['xref']} {img['width']}x{img['height']} "
                    f"bpc={img['bpc']} cs={img['colorspace']}"
                )
        print(f"Internal GoTo links: {total_goto}; URI links: {total_uri}")
        print(
            "Interpretation: a visible figure with many drawings/text objects but no single matching "
            "embedded image should be preserved with a vector PDF crop, not a screenshot."
        )
    doc.close()


if __name__ == "__main__":
    main()
