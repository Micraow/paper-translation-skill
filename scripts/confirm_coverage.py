#!/usr/bin/env python3
"""Confirm one already-reviewed set of coverage suggestions in a TSV ledger.

This command changes bookkeeping, not scientific accuracy. The operator must
first compare EVERY selected source block with rendered pages and translated
section/crop. Confirmation does not substitute for human/agent source review.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ledger", type=Path)
    ap.add_argument("--status", choices=("translated", "preserved", "nonprose"), required=True)
    ap.add_argument("--target", help="suggested_target to confirm; required for translated/preserved")
    ap.add_argument("--page", type=int, help="optionally confirm just one rendered source page")
    ap.add_argument("--project-root", type=Path, default=Path("."),
                    help="root for confirming target files (default: cwd)")
    ap.add_argument("--review-note", required=True, help="specific pages/assets checked, not just 'done'")
    args = ap.parse_args()
    if args.status in ("translated", "preserved") and not args.target:
        ap.error("translated/preserved confirmations must specify --target")
    if args.status == "nonprose" and args.target:
        ap.error("nonprose records must have no target")
    if len(args.review_note.strip()) < 12:
        ap.error("--review-note must record a meaningful comparison performed")
    with args.ledger.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        cols = list(reader.fieldnames or [])
        rows = list(reader)
    if not set(("source_id", "status", "suggested_status", "suggested_target", "notes", "target_file")) <= set(cols):
        ap.error("ledger needs suggestion columns; first run seed_coverage.py")
    picked = [r for r in rows if r["status"] == "todo"
              and r["suggested_status"] == args.status
              and r["suggested_target"] == (args.target or "")
              and (args.page is None or int(r["source_page"]) == args.page)]
    if not picked:
        ap.error("no matching unreviewed rows; inspect suggestions and arguments")
    if args.target and not (args.project_root / args.target).is_file():
        ap.error(f"target file not found relative to project root: {args.target}")
    for row in picked:
        row["status"] = args.status
        row["target_file"] = args.target or ""
        row["notes"] = args.review_note.strip()
    staged = args.ledger.with_suffix(args.ledger.suffix + ".tmp")
    with staged.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    staged.replace(args.ledger)
    pages = sorted({int(r["source_page"]) for r in picked})
    print(f"Confirmed {len(picked)} source blocks across source pages {pages} after external review.")
    print("Note: tool cannot verify translation correctness; only an actual source/target comparison can.")


if __name__ == "__main__":
    main()
