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

from pdf_assets import unique_images


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("out_dir", type=Path)
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    index = []

    for xref, first_page, _img in unique_images(doc):
        extracted = doc.extract_image(xref)
        ext = extracted.get("ext", "bin")
        name = f"xref-{xref:05d}.{ext}"
        (args.out_dir / name).write_bytes(extracted["image"])
        index.append({
            "xref": xref,
            "first_seen_page": first_page,
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
