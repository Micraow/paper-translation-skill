#!/usr/bin/env python3
"""Suggest source-block coverage mappings; NEVER declare translation complete.

The geometry and section-heading state machine dramatically reduce repetitive
TSV bookkeeping on two-column papers. Suggestions stay status=todo until an
agent reviews the source page against the actual translated/preserved target.
Every configured source heading must match exactly once, in document order.

Map schema (see assets/latex-template/assets/coverage-map.example.json):
  reading_order: "source" or "two-column"
  column_split_x: required for two-column, PDF points
  default_target: "sections/00-abstract.tex" (optional)
  headings: [{"match": "^1\\s+Introduction", "target_file": "sections/01-intro.tex"}]
  furniture_patterns: ["^USENIX Association"] (optional)
  caption_patterns: ["^Figure\\s+\\d+:"] (optional)
Geometry manifest uses the same format as extract_vector_regions.py; assets can
add kind="algorithm" or kind="figure".
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


def load_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def normalize_preview(text: str) -> str:
    return " ".join(re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "\ufffd", text).split())


def read_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cfg.get("headings"), list) or not cfg["headings"]:
        raise ValueError("coverage map must list source section headings in order")
    order = cfg.get("reading_order", "source")
    if order not in ("source", "two-column"):
        raise ValueError("reading_order must be 'source' or 'two-column'")
    if order == "two-column" and not isinstance(cfg.get("column_split_x"), (float, int)):
        raise ValueError("two-column mode requires explicit column_split_x (PDF points)")
    for entry in cfg["headings"]:
        if not entry.get("match") or not entry.get("target_file"):
            raise ValueError("every source heading needs match and target_file")
        re.compile(entry["match"], re.I)
    return cfg


def load_regions(path: Path | None, project_root: Path) -> dict[int, list[dict]]:
    if path is None:
        return {}
    cfg = json.loads(path.read_text(encoding="utf-8"))
    outdir = (path.parent / cfg.get("output_dir", "../figures")).resolve()
    out: dict[int, list[dict]] = {}
    for a in cfg.get("assets", []):
        bbox = a.get("bbox", [])
        if len(bbox) != 4 or float(bbox[0]) >= float(bbox[2]) or float(bbox[1]) >= float(bbox[3]):
            raise ValueError(f"invalid bbox for asset {a.get('output')}")
        destination = outdir / a["output"]
        if destination.suffix.lower() != ".pdf":
            destination = destination.with_suffix(".pdf")
        try:
            relative = destination.relative_to(project_root.resolve()).as_posix()
        except ValueError:
            raise ValueError(f"asset outside project directory: {destination}") from None
        out.setdefault(int(a["page"]), []).append({
            "bbox": tuple(map(float, bbox)), "target": relative,
            "kind": a.get("kind", "figure")
        })
    return out


def overlap_fraction(bbox: tuple[float, float, float, float], region: tuple[float, float, float, float]) -> float:
    x0, y0, x1, y1 = bbox
    a, b, c, d = region
    intersect = max(0, min(x1, c) - max(x0, a)) * max(0, min(y1, d) - max(y0, b))
    total = max(0.000001, (x1 - x0) * (y1 - y0))
    return intersect / total


def reading_sort_key(row: dict[str, str], cfg: dict) -> tuple:
    page = int(row["page"])
    x0, y0, x1 = (float(row[k]) for k in ("x0", "y0", "x1"))
    if cfg.get("reading_order") == "two-column":
        split = float(cfg["column_split_x"])
        # The first column must finish before the second. Wide blocks above
        # columns often contain titles; later spanning floats need manual QA.
        column = 1 if x0 >= split else 0
        if x0 < split < x1:
            column = 0
        return page, column, y0, x0, row["source_id"]
    return page, int(row.get("block", 0)), y0, x0, row["source_id"]


def suggest(rows: list[dict[str, str]], cfg: dict, regions: dict[int, list[dict]]) -> tuple[list[dict], list[str]]:
    patterns = [re.compile(h["match"], re.I) for h in cfg["headings"]]
    furniture = [re.compile(x, re.I) for x in cfg.get("furniture_patterns", [])]
    captions = [re.compile(x, re.I) for x in cfg.get("caption_patterns", [r"^(?:Figure|Fig\.|Table|Algorithm)\s+\d+\s*[:.]"])]
    records: dict[str, dict] = {}
    problems: list[str] = []
    active_target = cfg.get("default_target", "")
    active_status = "translated"
    current_heading = 0
    hits = Counter()
    for row in sorted(rows, key=lambda r: reading_sort_key(r, cfg)):
        sid = row["source_id"]
        if sid in records:
            problems.append(f"duplicate source ID: {sid}")
            continue
        preview = normalize_preview(row.get("text", ""))
        matches = [i for i, pat in enumerate(patterns) if pat.search(preview)]
        if len(matches) > 1:
            problems.append(f"{sid} matches multiple headings: {matches}; refine regexes")
        elif matches:
            i = matches[0]
            hits[i] += 1
            if i != current_heading:
                problems.append(
                    f"heading #{i+1} matched out of order at {sid}; "
                    f"expected #{current_heading+1}; check column order and regexes"
                )
            else:
                current_heading += 1
            active_target = cfg["headings"][i]["target_file"]
            active_status = cfg["headings"][i].get("status", "translated")
        candidate = active_status if active_target else "todo"
        target = active_target
        why = "chapter heading" if matches else "current source section"

        # A crop already includes its own internal text; suggest preservation
        # of that complete asset, not retranslation of chart tick labels.
        if all(k in row for k in ("x0", "y0", "x1", "y1")):
            bbox = tuple(float(row[k]) for k in ("x0", "y0", "x1", "y1"))
            overlaps = [a for a in regions.get(int(row["page"]), [])
                        if overlap_fraction(bbox, a["bbox"]) >= 0.82]
            if len(overlaps) > 1:
                problems.append(f"{sid} contained in multiple asset crops; inspect geometry")
            if overlaps:
                asset = overlaps[0]
                if asset["kind"] == "decoration":
                    candidate, target = "nonprose", ""
                else:
                    candidate, target = "preserved", asset["target"]
                why = f"inside {asset['kind']} asset; verify crop and text visually"
        if not matches and any(pat.search(preview) for pat in furniture):
            candidate, target, why = "nonprose", "", "repeated page furniture; verify before excluding"
        elif not matches and any(pat.search(preview) for pat in captions) and candidate != "preserved":
            candidate, target, why = (active_status if active_target else "todo"), active_target, "figure/table caption; translate separately"
        records[sid] = {
            "source_id": sid,
            "source_page": row["page"],
            "status": "todo",             # Never automatically certify completeness.
            "target_file": "",
            "notes": "",
            "source_preview": preview[:180],
            "suggested_status": candidate,
            "suggested_target": target,
            "suggestion_reason": why,
        }
    for i, rule in enumerate(cfg["headings"]):
        if hits[i] != 1:
            problems.append(f"required heading #{i+1} {rule['match']!r} matched {hits[i]} time(s), expected exactly 1")
    if current_heading != len(cfg["headings"]):
        problems.append(f"consumed {current_heading}/{len(cfg['headings'])} headings; refusing unreliable chapter mapping")
    return [records[r["source_id"]] for r in rows if r["source_id"] in records], problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_blocks", type=Path, help="TSV from extract_text_blocks.py")
    ap.add_argument("--headings", type=Path, required=True, help="source section regexes in order")
    ap.add_argument("--regions", type=Path, help="optional assets/regions.json")
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--force", action="store_true", help="explicitly REPLACE an existing populated ledger")
    args = ap.parse_args()
    rows = load_tsv(args.source_blocks)
    for col in ("source_id", "page", "x0", "y0", "x1", "y1", "text"):
        if any(col not in row for row in rows):
            ap.error(f"source blocks missing column: {col}")
    try:
        cfg = read_config(args.headings)
        regions = load_regions(args.regions, args.project_root)
        suggested, problems = suggest(rows, cfg, regions)
    except (ValueError, KeyError, re.error) as exc:
        ap.error(str(exc))
    if problems:
        for msg in problems[:25]:
            print("ERROR:", msg)
        raise SystemExit("Coverage seed NOT written. Fix heading/geometry mapping first.")
    if args.output.exists() and not args.force:
        try:
            previous = load_tsv(args.output)
        except (OSError, csv.Error) as exc:
            ap.error(f"cannot safely inspect existing ledger {args.output}: {exc}")
        if previous:
            ap.error(f"existing ledger has {len(previous)} rows; refusing to overwrite reviewed work. "
                     "Back it up and use --force only if intentional")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    staged = args.output.with_suffix(args.output.suffix + ".tmp")
    with staged.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(suggested[0]) if suggested else [
            "source_id", "source_page", "status", "target_file", "notes", "source_preview",
            "suggested_status", "suggested_target", "suggestion_reason"], delimiter="\t")
        w.writeheader()
        w.writerows(suggested)
    staged.replace(args.output)
    counts = Counter(r["suggested_status"] for r in suggested)
    print(f"Seeded {len(suggested)} unreviewed blocks (all status=todo) at {args.output}")
    print("Suggested classes:", dict(counts))
    print("All source headings matched exactly once; verify source page/column order before signing off.")


if __name__ == "__main__":
    main()
