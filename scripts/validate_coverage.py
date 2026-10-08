#!/usr/bin/env python3
"""Check source-block coverage and explicitly recorded translation decisions.

A ledger is a *traceability* check, not proof of translation accuracy. Read and
compare the actual prose against the source PDF before claiming completeness.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

ALLOWED = {"translated", "preserved", "nonprose", "skip-with-reason", "todo"}


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"Missing TSV file: {path}. Generate source blocks and complete the coverage ledger before release.")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def validate(ledger: Path, blocks: Path | None = None, require_nonempty: bool = False,
             require_targets: bool = False, root: Path | None = None, allow_todo: bool = False) -> list[str]:
    rows = read_tsv(ledger)
    errors: list[str] = []
    if require_nonempty and not rows:
        errors.append("coverage ledger is empty")
    ids = [r.get("source_id", "").strip() for r in rows]
    dupes = sorted(k for k, v in Counter(ids).items() if k and v > 1)
    if dupes:
        errors.append(f"duplicate source IDs: {dupes[:15]}")
    if any(not k for k in ids):
        errors.append("blank source IDs")
    if blocks is not None:
        source_rows = read_tsv(blocks)
        expected = {r["source_id"] for r in source_rows}
        if len(expected) != len(source_rows):
            errors.append("duplicate block IDs in source blocks")
        missing = sorted(expected - set(ids))
        extra = sorted(set(ids) - expected)
        if missing:
            errors.append(f"missing source blocks: {missing[:15]} ({len(missing)} total)")
        if extra:
            errors.append(f"unknown source block IDs: {extra[:15]} ({len(extra)} total)")
    for i, r in enumerate(rows, 2):
        status = r.get("status", "").strip()
        if status not in ALLOWED:
            errors.append(f"row {i}: invalid status: {status!r}")
        if status == "todo" and not allow_todo:
            errors.append(f"row {i}: still TODO")
        if status == "skip-with-reason" and not r.get("notes", "").strip():
            errors.append(f"row {i}: skipped text requires a reason")
        if require_targets and status in ("translated", "preserved"):
            dest = r.get("target_file", "").strip()
            if not dest:
                errors.append(f"row {i}: translated/preserved block needs target_file")
            elif root is not None and not (root / dest).is_file():
                errors.append(f"row {i}: target_file does not exist: {dest}")
    return errors


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ledger", type=Path)
    ap.add_argument("--source-blocks", type=Path)
    ap.add_argument("--require-nonempty", action="store_true")
    ap.add_argument("--require-targets", action="store_true")
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--allow-todo", action="store_true")
    args = ap.parse_args()
    problems = validate(args.ledger, args.source_blocks, args.require_nonempty,
                        args.require_targets, args.root, args.allow_todo)
    if problems:
        for problem in problems[:40]:
            print("ERROR:", problem)
        raise SystemExit(1)
    print("Coverage ledger OK (structural traceability only; semantic comparison still required)")


if __name__ == "__main__":
    main()
