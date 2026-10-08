#!/usr/bin/env python3
"""Extract text blocks and optionally seed a translation-coverage ledger.

The block order is a retrieval aid, not authoritative reading order for complex
multi-column pages. Always verify against rendered pages.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import fitz


CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean_text(text: str, keep_raw: bool = False) -> str:
    # Some PDF symbol fonts incorrectly map glyphs to C0 controls. Replace
    # the invalid glyph with U+FFFD instead of joining adjacent text together
    # and silently pretending the extraction was faithful.
    text = text.replace("\u00ad", "")
    if keep_raw:
        # Preserve even control characters that Python considers whitespace.
        # This intentionally produces potentially viewer-hostile debugging TSV.
        return text.replace("\r", " ").replace("\n", " ").replace("\t", " ").strip(" ")
    text = CONTROL_RE.sub("\ufffd", text)
    return " ".join(text.split())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--tsv", type=Path, required=True)
    ap.add_argument("--coverage", type=Path)
    ap.add_argument("--keep-raw", action="store_true",
                    help="keep raw control characters (unsafe for many text viewers)")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    args.tsv.parent.mkdir(parents=True, exist_ok=True)
    coverage_rows = []

    with args.tsv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["source_id", "page", "block", "x0", "y0", "x1", "y1", "text"])
        for pno, page in enumerate(doc):
            blocks = page.get_text("blocks")
            for idx, block in enumerate(blocks, start=1):
                x0, y0, x1, y1, text, *_ = block
                text = clean_text(text, keep_raw=args.keep_raw)
                if not text:
                    continue
                source_id = f"p{pno + 1:03d}-b{idx:03d}"
                w.writerow([
                    source_id,
                    pno + 1,
                    idx,
                    f"{x0:.2f}",
                    f"{y0:.2f}",
                    f"{x1:.2f}",
                    f"{y1:.2f}",
                    text,
                ])
                coverage_rows.append([source_id, pno + 1, "todo", "", "", text[:180]])

    if args.coverage:
        args.coverage.parent.mkdir(parents=True, exist_ok=True)
        with args.coverage.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["source_id", "source_page", "status", "target_file", "notes", "source_preview"])
            w.writerows(coverage_rows)

    doc.close()
    print(f"Wrote text blocks: {args.tsv}")
    if args.coverage:
        print(f"Seeded all-TODO coverage ledger: {args.coverage} (see seed_coverage.py for chapter proposals)")


if __name__ == "__main__":
    main()
