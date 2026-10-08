#!/usr/bin/env python3
"""Restore internal GoTo links from numeric citations to bibliography entries.

Designed for translated PDFs that preserve the bibliography as imported original
PDF pages. Common citation forms: [1], [3, 5, 9], [3-5], [3–5].
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import fitz

CIT_RE = re.compile(r"\[((?:\s*[1-9]\d*\s*)(?:(?:,|–|-)\s*[1-9]\d*\s*)*)\]")
REF_LABEL_RE = re.compile(r"\[([1-9]\d*)\]")


def find_reference_start(doc: fitz.Document) -> int:
    candidates = []
    for pno, page in enumerate(doc):
        text = page.get_text("text")
        lower = text.lower()
        heading = (
            "references" in lower
            or "bibliography" in lower
            or "参考文献" in text
        )
        labels = {int(x) for x in REF_LABEL_RE.findall(text)}
        if heading and labels:
            return pno
        if len(labels) >= 6:
            candidates.append((pno, len(labels)))
    if candidates:
        return max(candidates, key=lambda x: x[1])[0]
    raise RuntimeError("Could not auto-detect bibliography start; pass --ref-start-page")


def build_targets(doc: fitz.Document, start: int, end: int) -> dict[int, tuple[int, fitz.Point]]:
    targets: dict[int, tuple[int, fitz.Point]] = {}
    for pno in range(start, end + 1):
        page = doc[pno]
        text = page.get_text("text")
        nums = sorted({int(x) for x in REF_LABEL_RE.findall(text)})
        for n in nums:
            if n in targets:
                continue
            hits = page.search_for(f"[{n}]")
            if not hits:
                continue
            r = hits[0]
            targets[n] = (pno, fitz.Point(max(0, r.x0 - 6), max(0, r.y0 - 12)))
    if not targets:
        raise RuntimeError("No numbered bibliography labels found in selected reference pages")
    return targets


def rect_already_linked(page: fitz.Page, rect: fitz.Rect, target_page: int) -> bool:
    """Suppress actual duplicate annotations, NOT nearby adjacent citations.

    Two references on successive tight lines can have slightly overlapping
    glyph rectangles. Rejecting on *any* overlap silently loses hyperlinks.
    """
    for link in page.get_links():
        if link.get("kind") not in (fitz.LINK_GOTO, fitz.LINK_NAMED):
            continue
        if link.get("page") != target_page:
            continue
        existing = fitz.Rect(link.get("from"))
        overlap = (existing & rect).get_area()
        if overlap > 0 and overlap / max(rect.get_area(), 1e-8) >= 0.80:
            return True
    return False


def add_links(doc: fitz.Document, ref_start: int, ref_end: int) -> tuple[int, dict[int, int]]:
    targets = build_targets(doc, ref_start, ref_end)
    inserted = 0
    per_ref: dict[int, int] = {}

    for pno in range(ref_start):
        page = doc[pno]
        text = page.get_text("text")
        groups = sorted({m.group(0) for m in CIT_RE.finditer(text)}, key=len, reverse=True)
        for group in groups:
            group_hits = page.search_for(group)
            if not group_hits:
                continue
            nums = [int(x) for x in re.findall(r"\d+", group)]
            for gr in group_hits:
                for n in nums:
                    if n not in targets:
                        continue
                    # Search the printed numeral inside the group rectangle. This is
                    # intentionally visual: collapsed ranges only expose endpoints.
                    subhits = page.search_for(str(n), clip=gr)
                    for sr in subhits:
                        # Avoid linking a digit that is clearly only a substring of a
                        # larger visible number when we can infer that from width.
                        if sr.width <= 0 or sr.height <= 0:
                            continue
                        link_rect = fitz.Rect(sr.x0 - 0.5, sr.y0 - 0.6, sr.x1 + 0.5, sr.y1 + 0.6)
                        target_page, target_point = targets[n]
                        if rect_already_linked(page, link_rect, target_page):
                            continue
                        page.insert_link({
                            "kind": fitz.LINK_GOTO,
                            "from": link_rect,
                            "page": target_page,
                            "to": target_point,
                            "zoom": 0.0,
                        })
                        inserted += 1
                        per_ref[n] = per_ref.get(n, 0) + 1
    return inserted, per_ref


def privatize_shared_annotation_arrays(doc: fitz.Document) -> int:
    """Avoid accidental cross-page link replication from a shared /Annots xref.

    Some PDF rewriting/annotation-stripping tools leave multiple page objects
    pointing at the same empty annotations array. Mutating it for one page then
    mutates all of those pages. Copy the array inline on each affected page.
    """
    owners: dict[int, list[int]] = {}
    for pno in range(len(doc)):
        page_xref = doc.page_xref(pno)
        kind, value = doc.xref_get_key(page_xref, "Annots")
        if kind == "xref":
            xref = int(value.split()[0])
            owners.setdefault(xref, []).append(page_xref)
    copied = 0
    for annots_xref, pages in owners.items():
        if len(pages) <= 1:
            continue
        raw_array = doc.xref_object(annots_xref).strip()
        if not raw_array.startswith("[") or not raw_array.endswith("]"):
            continue
        for page_xref in pages:
            doc.xref_set_key(page_xref, "Annots", raw_array)
            copied += 1
    return copied


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--ref-start-page", type=int, help="1-based final-PDF page number")
    ap.add_argument("--ref-end-page", type=int, help="1-based final-PDF page number")
    ap.add_argument("--report", type=Path, help="write JSON report")
    ap.add_argument("--strict", action="store_true", help="fail on missing citation links/targets")
    args = ap.parse_args()

    doc = fitz.open(args.input)
    start = args.ref_start_page - 1 if args.ref_start_page else find_reference_start(doc)
    end = args.ref_end_page - 1 if args.ref_end_page else len(doc) - 1
    if not (0 <= start <= end < len(doc)):
        raise SystemExit("Invalid bibliography page range")

    privatized_pages = privatize_shared_annotation_arrays(doc)
    targets = build_targets(doc, start, end)
    inserted, per_ref = add_links(doc, start, end)
    # Reload modified pages; PyMuPDF caches annotations until a reload.
    for pno in range(start):
        doc.reload_page(doc[pno])

    # Verify that every printed number in each detected citation group has a
    # destination. This is not a substitute for manual link-target spot checks.
    missing_targets: set[int] = set()
    unlinked: list[dict[str, object]] = []
    citation_groups = 0
    for pno in range(start):
        page = doc[pno]
        page_links = page.get_links()
        groups = sorted(set(m.group(0) for m in CIT_RE.finditer(page.get_text("text"))))
        for group in groups:
            for rect in page.search_for(group):
                citation_groups += 1
                for n in [int(v) for v in re.findall(r"\d+", group)]:
                    if n not in targets:
                        missing_targets.add(n)
                        continue
                    pieces = page.search_for(str(n), clip=rect)
                    target_page = targets[n][0]
                    linked = any(
                        link.get("kind") == fitz.LINK_GOTO
                        and link.get("page") == target_page
                        and any(not (fitz.Rect(link["from"]) & part).is_empty for part in pieces)
                        for link in page_links
                    )
                    if not linked:
                        unlinked.append({"page": pno + 1, "citation": group, "reference": n})
    if args.strict and (missing_targets or unlinked or (citation_groups > 0 and inserted == 0)):
        raise SystemExit(f"Link restoration FAILED: missing_targets={sorted(missing_targets)} unlinked={unlinked[:8]} inserted={inserted}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(args.output, garbage=4, deflate=True, clean=True)
    doc.close()

    report = {
        "input": str(args.input),
        "output": str(args.output),
        "reference_start_page": start + 1,
        "reference_end_page": end + 1,
        "reference_targets": sorted(targets),
        "privatized_annotation_arrays": privatized_pages,
        "inserted_links": inserted,
        "citation_groups": citation_groups,
        "missing_reference_targets": sorted(missing_targets),
        "unlinked_citations": unlinked,
        "links_per_reference": {str(k): v for k, v in sorted(per_ref.items())},
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
