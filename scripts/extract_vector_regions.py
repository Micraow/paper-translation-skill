#!/usr/bin/env python3
"""Extract selected page regions as standalone vector-preserving PDFs.

Manifest format:
{
  "source": "../sources/original.pdf",
  "output_dir": "../figures",
  "assets": [
    {"output":"fig1.pdf", "page":3, "bbox":[x0,y0,x1,y1], "label":"..."}
  ]
}
Paths are resolved relative to the manifest file.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz


def resolve(base: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (base / p).resolve()


def preview_pdf(pdf_path: Path, out_png: Path, dpi: int = 180) -> None:
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    pix.save(out_png)
    doc.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--preview-dir", type=Path)
    args = ap.parse_args()

    manifest_path = args.manifest.resolve()
    base = manifest_path.parent
    cfg = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = cfg.get("assets", [])
    if not assets:
        print("No regions configured; skipping vector extraction")
        return
    source = resolve(base, cfg["source"])
    output_dir = resolve(base, cfg.get("output_dir", "../figures"))
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(source)
    count = 0
    for item in assets:
        page_no = int(item["page"])
        if not 1 <= page_no <= len(doc):
            raise ValueError(f"{item.get('output')}: page {page_no} out of range")
        coords = item["bbox"]
        if len(coords) != 4:
            raise ValueError(f"{item.get('output')}: bbox must contain four numbers")
        clip = fitz.Rect(*map(float, coords))
        page_rect = doc[page_no - 1].rect
        if clip.is_empty or clip.x0 < page_rect.x0 or clip.y0 < page_rect.y0 or clip.x1 > page_rect.x1 or clip.y1 > page_rect.y1:
            raise ValueError(
                f"{item.get('output')}: bbox {tuple(clip)} outside page bounds {tuple(page_rect)}"
            )

        output_name = item["output"]
        if not output_name.lower().endswith(".pdf"):
            output_name += ".pdf"
        dst = output_dir / output_name

        out = fitz.open()
        new_page = out.new_page(width=clip.width, height=clip.height)
        new_page.show_pdf_page(
            new_page.rect,
            doc,
            page_no - 1,
            clip=clip,
            keep_proportion=False,
        )
        out.save(dst, garbage=4, deflate=True)
        out.close()
        count += 1
        label = item.get("label", "")
        print(f"extracted {dst.name} from page {page_no} {label}")

        if args.preview_dir:
            preview_pdf(dst, args.preview_dir / f"{Path(output_name).stem}.png")

    doc.close()
    print(f"Extracted {count} vector-preserving regions -> {output_dir}")


if __name__ == "__main__":
    main()
