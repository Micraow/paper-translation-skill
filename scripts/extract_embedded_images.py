#!/usr/bin/env python3
"""Extract raw embedded raster image objects from a PDF.

This does NOT reconstruct figures made of vector paths, text, or multiple image
objects. Use vector-region extraction for those.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("out_dir", type=Path)
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    seen: set[int] = set()
    index = []

    for pno, page in enumerate(doc):
        for img in page.get_images(full=True):
            xref = int(img[0])
            if xref in seen:
                continue
            seen.add(xref)
            extracted = doc.extract_image(xref)
            ext = extracted.get("ext", "bin")
            data = extracted["image"]
            name = f"xref-{xref:05d}.{ext}"
            path = args.out_dir / name
            path.write_bytes(data)
            index.append({
                "xref": xref,
                "first_seen_page": pno + 1,
                "file": name,
                "width": extracted.get("width"),
                "height": extracted.get("height"),
                "colorspace": extracted.get("colorspace"),
                "bpc": extracted.get("bpc"),
            })

    (args.out_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    doc.close()
    print(f"Extracted {len(index)} unique embedded raster image objects -> {args.out_dir}")
    print("Note: a complete scholarly figure may still require a vector PDF crop.")


if __name__ == "__main__":
    main()
