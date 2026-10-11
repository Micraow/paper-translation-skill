#!/usr/bin/env python3
r"""Query a source-blocks TSV without loading the whole table into context.

`work/source-blocks.tsv` (from extract_text_blocks.py) is the authoritative block
inventory but grows past 90 KB on real two-column papers. Re-reading it every turn is
the largest avoidable input cost in a translation run. This tool prints only the rows
you ask for, so the full table never has to enter the model context again.

It reads text only: no PDF, no coverage logic, and it never changes a ledger status.

Examples:
    blocks.py query work/source-blocks.tsv --page 7
    blocks.py query work/source-blocks.tsv --page-range 4-6 --kind caption
    blocks.py query work/source-blocks.tsv --grep 'Figure 4' --width 60
    blocks.py query work/source-blocks.tsv --id p007-b004 --json
    blocks.py index work/source-blocks.tsv --out work/blocks-index.tsv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

CAPTION_RE = re.compile(r"^(?:Figure|Fig\.|Table|Algorithm)\s*\d+", re.I)
HEADING_RE = re.compile(r"^(?:Abstract|References|Acknowledg\w*|\d+(?:\.\d+)*\s+\S)")
EQUATION_RE = re.compile(r"\((\d+[a-z]?)\)\s*$")


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"ERROR: source blocks not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if not rows:
        raise SystemExit(f"ERROR: source blocks are empty: {path}")
    if "source_id" not in rows[0] or "text" not in rows[0]:
        raise SystemExit("ERROR: expected at least source_id and text columns")
    return rows


def classify(row: dict[str, str]) -> str:
    if row.get("kind"):
        return row["kind"]
    text = (row.get("text") or "").strip()
    if CAPTION_RE.match(text):
        return "caption"
    if HEADING_RE.match(text):
        return "heading"
    if EQUATION_RE.search(text):
        return "equation"
    return "prose"


def parse_page_range(spec: str) -> tuple[int, int]:
    parts = spec.split("-", 1)
    if len(parts) != 2:
        raise SystemExit("ERROR: --page-range must look like 4-6")
    try:
        lo, hi = int(parts[0]), int(parts[1])
    except ValueError:
        raise SystemExit("ERROR: --page-range must look like 4-6") from None
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def select(rows: list[dict[str, str]], args) -> list[dict[str, str]]:
    out = rows
    if args.page is not None:
        out = [r for r in out if str(r.get("page")) == str(args.page)]
    if args.page_range:
        lo, hi = parse_page_range(args.page_range)
        out = [r for r in out if lo <= int(r.get("page") or 0) <= hi]
    if args.id:
        wanted = set(args.id)
        out = [r for r in out if r["source_id"] in wanted]
    if args.kind and args.kind != "all":
        out = [r for r in out if classify(r) == args.kind]
    if args.grep:
        flags = 0 if args.case_sensitive else re.I
        try:
            rx = re.compile(args.grep, flags)
        except re.error as exc:
            raise SystemExit(f"ERROR: bad --grep regex: {exc}") from None
        out = [r for r in out if rx.search(r.get("text", ""))]
    return out


def preview(text: str, width: int) -> str:
    flat = " ".join((text or "").split())
    return flat if len(flat) <= width else flat[: max(0, width - 1)] + "…"


def cmd_query(args) -> int:
    rows = select(read_tsv(args.source_blocks), args)
    if args.limit:
        rows = rows[: args.limit]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("0 matching blocks (check --page / --grep / --id)")
        return 0
    print(f"# {len(rows)} block(s)")
    for r in rows:
        text = (r.get("text") or "") if args.full_text else preview(r.get("text", ""), args.width)
        print(f"{r['source_id']}\tp{r.get('page','?')}\t{classify(r)}\t{text}")
    return 0


def cmd_index(args) -> int:
    rows = read_tsv(args.source_blocks)
    header = ("source_id", "page", "kind", "preview")
    for width in (args.preview, 60, 40, 24, 0):
        body = [[r["source_id"], str(r.get("page", "?")), classify(r), preview(r.get("text", ""), width)]
                for r in rows]
        blob = "\n".join("\t".join(row) for row in body)
        if len(blob.encode("utf-8")) <= args.max_bytes or width == 0:
            break
    lines = ["\t".join(header)] + ["\t".join(row) for row in body]
    content = "\n".join(lines) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(content, encoding="utf-8")
    print(f"Wrote compact index: {args.out} ({len(content.encode('utf-8'))} bytes, {len(rows)} blocks, preview={width})")
    print("Read this index by default; use `blocks.py query` for any specific block.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    q = sub.add_parser("query", help="print only the matching blocks")
    q.add_argument("source_blocks", type=Path)
    q.add_argument("--page", type=int)
    q.add_argument("--page-range", help="inclusive, e.g. 4-6")
    q.add_argument("--id", action="append", default=[], help="source_id (repeatable)")
    q.add_argument("--kind", choices=("all", "prose", "caption", "heading", "equation", "figure", "algorithm"),
                   default="all")
    q.add_argument("--grep", help="regular expression over the extracted text (case-insensitive by default)")
    q.add_argument("--case-sensitive", action="store_true")
    q.add_argument("--width", type=int, default=100, help="text preview width")
    q.add_argument("--full-text", action="store_true", help="print the complete extracted text")
    q.add_argument("--limit", type=int, default=0)
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_query)

    i = sub.add_parser("index", help="write a size-capped compact index of all blocks")
    i.add_argument("source_blocks", type=Path)
    i.add_argument("--out", type=Path, default=Path("work/blocks-index.tsv"))
    i.add_argument("--max-bytes", type=int, default=16384)
    i.add_argument("--preview", type=int, default=100)
    i.set_defaults(func=cmd_index)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
