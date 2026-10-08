#!/usr/bin/env python3
"""Build compact, *loss-accounted* source packets for one-section-at-a-time translation.

This script is a context router, not a translator and NOT a coverage validator.
No 'todo' ledger entries are confirmed by generating packets. Every source block
stays accounted for in the JSON index, including preserved, nonprose and unmapped.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from seed_coverage import reading_sort_key


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def slug(target: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", target).strip("-").lower()[:55]
    return (safe or "unmapped") + "-" + hashlib.sha256(target.encode()).hexdigest()[:7]


def target_for(row: dict[str, str]) -> str:
    # An accepted target overrides a suggestion. Never turn an unreviewed
    # suggestion into a completed coverage record.
    if row.get("status") and row["status"] != "todo":
        return row.get("target_file") or "__confirmed_nonprose__"
    return row.get("suggested_target") or "__needs_mapping__"


def kind_for(row: dict[str, str]) -> str:
    return row.get("status") if row.get("status") not in ("", "todo", None) else row.get("suggested_status", "todo")


def glossary_lines(path: Path | None, text: str) -> list[str]:
    if path is None or not path.exists():
        return []
    rows = read_tsv(path)
    if not rows:
        return []
    keys = list(rows[0])
    src = next((k for k in keys if k.lower() in ("source", "source_term", "english", "term", "original")), keys[0])
    dst = next((k for k in keys if k.lower() in ("target", "translation", "chinese", "translated")), keys[1] if len(keys) > 1 else keys[0])
    matched = []
    for row in rows:
        word, translated = row.get(src, "").strip(), row.get(dst, "").strip()
        if word and translated and re.search(r"(?<![\w])" + re.escape(word) + r"(?![\w])", text, flags=re.I):
            matched.append(f"- {word} → {translated}")
    return matched


def make_entry(ledger_row: dict[str, str], source_row: dict[str, str]) -> str:
    sid = ledger_row["source_id"]
    page = source_row.get("page", ledger_row.get("source_page", "?"))
    kind = kind_for(ledger_row)
    actual_status = ledger_row.get("status", "todo")
    label = f"[{sid} · p.{page} · {kind}; ledger={actual_status}]"
    original = source_row.get("text", "").strip()
    if "\ufffd" in original:
        label += " [EXTRACTION UNCERTAIN: inspect source rendering]"
    if actual_status == "nonprose":
        # Once manually confirmed, repetition need not reenter model context.
        return f"{label} Previously reviewed as nonprose; see ledger for reason."
    if kind == "preserved":
        asset = target_for(ledger_row)
        return f"{label} Preserved original asset/reference: {asset}. Verify visually; do not retranslate source pseudocode."
    if kind == "skip-with-reason":
        return f"{label} Reviewed exclusion: {ledger_row.get('notes', '')}"
    if not original:
        return f"{label} No reliable extracted text; inspect source PDF page."
    return f"{label}\n{original}"


def build_packets(
    *, sources: Path, ledger: Path, config: Path, out_dir: Path,
    max_chars: int, pending_only: bool, selected: list[str],
    glossary: Path | None, force: bool,
) -> dict:
    if max_chars < 1500:
        raise ValueError("--max-chars must be at least 1500; do not fragment paragraphs into tiny prompts")
    src_rows = read_tsv(sources)
    cov_rows = read_tsv(ledger)
    cfg = json.loads(config.read_text(encoding="utf-8"))
    src_by_id = {r["source_id"]: r for r in src_rows}
    cov_by_id = {r["source_id"]: r for r in cov_rows}
    if len(src_by_id) != len(src_rows) or len(cov_by_id) != len(cov_rows):
        raise ValueError("duplicate source_id in source blocks / coverage ledger")
    if set(src_by_id) != set(cov_by_id):
        raise ValueError(f"source ledger mismatch: {len(set(src_by_id) ^ set(cov_by_id))} IDs differ; regenerate/check ledger")
    grouped: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    counts: dict[str, int] = Counter()
    available: dict[str, int] = Counter()
    pending: dict[str, int] = Counter()
    for source in sorted(src_rows, key=lambda s: reading_sort_key(s, cfg)):
        record = cov_by_id[source["source_id"]]
        counts[record.get("status", "todo")] += 1
        group = target_for(record)
        available[group] += 1
        if record.get("status") == "todo":
            pending[group] += 1
        if pending_only and record.get("status") != "todo":
            continue
        if selected and group not in selected:
            continue
        grouped[group].append((source, record))
    if selected and not grouped:
        raise ValueError("--target did not match any pending block; consult coverage.tsv suggested_target/target_file")
    entries = []
    staged: list[tuple[Path, str]] = []
    for group, pairs in grouped.items():
        sections: list[list[tuple[dict, dict, str]]] = []
        current: list[tuple[dict, dict, str]] = []
        length = 0
        for source, record in pairs:
            content = make_entry(record, source)
            # Never split a PDF extraction block: formulas / paragraphs may be
            # damaged by truncation. Make an oversized packet if necessary.
            if current and length + len(content) + 2 > max_chars:
                sections.append(current)
                current, length = [], 0
            current.append((source, record, content))
            length += len(content) + 2
        if current:
            sections.append(current)
        for index, section in enumerate(sections, 1):
            ids = [r["source_id"] for _, r, _ in section]
            pages = sorted({int(s["page"]) for s, _, _ in section})
            body = "\n\n".join(t for _, _, t in section)
            glossary_matches = glossary_lines(glossary, body)
            glos = "\n".join(glossary_matches) if glossary_matches else "(none matched in this packet)"
            head = (
                f"# Source packet: {group}\n"
                f"Part {index}/{len(sections)} · {len(section)} source blocks · source pages {','.join(map(str,pages))}\n\n"
                "**This is a location-oriented aid, not guaranteed faithful extracted text.** "
                "Compare technical formulas, glyphs, column/page boundaries, and figures against the rendered PDF. "
                "Do not translate blocks marked as preserved. Do not treat candidate coverage labels as reviewed.\n\n"
                f"Relevant pre-approved terminology:\n{glos}\n\n"
                "## Original material (one block per source ID)\n\n"
            )
            filename = f"{slug(group)}-part{index:02d}.md"
            staged.append((out_dir / filename, head + body + "\n"))
            entries.append({
                "target": group, "file": filename,
                "part": index, "total_parts": len(sections),
                "source_ids": ids, "source_pages": pages,
                "statuses": dict(Counter(kind_for(r) for _, r, _ in section)),
            })
    index = {
        "source": str(sources), "ledger": str(ledger),
        "counts_by_verified_status": dict(counts),
        "all_targets": dict(sorted(available.items())),
        "pending_by_target": dict(sorted(pending.items())),
        "entries": entries,
        "all_source_blocks_accounted": len(src_by_id) == len(cov_by_id) and set(src_by_id) == set(cov_by_id),
        "generated_packets_are_not_evidence_of_translation": True,
        "pending_only": pending_only, "selected_targets": selected,
    }
    staged.append((out_dir / "index.json", json.dumps(index, ensure_ascii=False, indent=2) + "\n"))
    short = [
        "# Compact section index (choose ONE packet to open)",
        "", "Status: source-block / coverage ID equality verified. Packet creation does NOT review/translate source.",
        f"Total source blocks: {len(src_by_id)}; packetized now: {sum(len(x['source_ids']) for x in entries)}; "
        f"currently pending: {sum(pending.values())}.", "",
        "| Target / output packet | Source blocks | Pages | Translation kind |", "|---|---:|---|---|",
    ]
    for item in entries:
        short.append(
            f"| `{item['target']}` → `{item['file']}` | {len(item['source_ids'])} | "
            f"{','.join(map(str,item['source_pages']))} | {','.join(f'{k}:{v}' for k,v in item['statuses'].items())} |"
        )
    if len(available) != len(grouped):
        short.extend(["", "Unselected source groups remain in `index.json` and the coverage ledger; "
                      "they have not been silently approved."])
    staged.append((out_dir / "index.md", "\n".join(short) + "\n"))
    # Refuse to trample possible manually annotated packets. Also avoid writing
    # a half-updated set if any output file conflicts.
    for path, content in staged:
        if path.exists() and path.read_text(encoding="utf-8") != content and not force:
            raise ValueError(f"refusing to replace changed {path}; pass --force after checking")
    out_dir.mkdir(parents=True, exist_ok=True)
    for path, content in staged:
        path.write_text(content, encoding="utf-8")
    return index


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-blocks", type=Path, default=Path("work/source-blocks.tsv"))
    ap.add_argument("--ledger", type=Path, default=Path("work/coverage.tsv"))
    ap.add_argument("--headings", type=Path, default=Path("assets/coverage-map.json"))
    ap.add_argument("--out-dir", type=Path, default=Path("work/context-packets"))
    ap.add_argument("--max-chars", type=int, default=12000)
    ap.add_argument("--pending-only", action="store_true", help="only packetize not-yet-reviewed source IDs")
    ap.add_argument("--target", action="append", default=[], help="exact suggested_target or target_file (repeatable)")
    ap.add_argument("--glossary", type=Path, default=Path("work/glossary.tsv"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    try:
        result = build_packets(
            sources=args.source_blocks, ledger=args.ledger, config=args.headings,
            out_dir=args.out_dir, max_chars=args.max_chars,
            pending_only=args.pending_only, selected=args.target,
            glossary=args.glossary, force=args.force,
        )
    except (ValueError, FileNotFoundError) as exc:
        ap.exit(2, f"ERROR: {exc}\n")
    print(f"Prepared {len(result['entries'])} packets; {sum(len(x['source_ids']) for x in result['entries'])} source IDs selected.")
    print(f"Short index: {args.out_dir / 'index.md'} (open only the section packet(s) needed)")
    print("Note: coverage statuses unchanged; final PDF/source visual comparison is still mandatory.")


if __name__ == "__main__":
    main()
