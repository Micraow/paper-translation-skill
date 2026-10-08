#!/usr/bin/env python3
"""Audit translated PDF structure, text, hyperlinks and bibliography pointers."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import fitz

CIT_RE = re.compile(r"\[((?:\s*[1-9]\d*\s*)(?:(?:,|–|-)\s*[1-9]\d*\s*)*)\]")
REF_RE = re.compile(r"\[([1-9]\d*)\]")


def reference_start(doc: fitz.Document) -> int | None:
    for i, page in enumerate(doc):
        text = page.get_text("text")
        if any(h in text.lower() for h in ("references", "bibliography", "参考文献")) and REF_RE.search(text):
            return i
    return None


def audit(pdf: Path, mode: str, strict: bool, ref_start_page: int | None = None) -> dict:
    doc = fitz.open(pdf)
    start = ref_start_page - 1 if ref_start_page else reference_start(doc)
    fonts: Counter = Counter()
    goto = named = uri = citation_groups = 0
    errors: list[str] = []
    warnings: list[str] = []
    replacement: list[int] = []
    details: list[dict] = []
    all_refs = set()
    if start is not None:
        if not (0 <= start < len(doc)):
            errors.append(f"reference start page out of range: {start+1}")
        else:
            for page in list(doc)[start:]:
                all_refs.update(map(int, REF_RE.findall(page.get_text("text"))))
    for pno, page in enumerate(doc):
        text = page.get_text("text")
        if "\ufffd" in text:
            replacement.append(pno + 1)
        for f in page.get_fonts(full=True):
            fonts[str(f[3])] += 1
        links = page.get_links()
        goto_here = sum(x.get("kind") == fitz.LINK_GOTO for x in links)
        named_here = sum(x.get("kind") == fitz.LINK_NAMED and x.get("page", -1) >= 0 for x in links)
        goto += goto_here
        named += named_here
        uri += sum(x.get("kind") == fitz.LINK_URI for x in links)
        for link in links:
            if link.get("kind") in (fitz.LINK_GOTO, fitz.LINK_NAMED) and not (0 <= link.get("page", -1) < len(doc)):
                errors.append(f"page {pno+1}: out-of-range internal link")
        groups = list(CIT_RE.finditer(text)) if start is None or pno < start else []
        citation_groups += len(groups)
        unlinked_here = 0
        if strict and groups:
            for phrase in {g.group(0) for g in groups}:
                for region in page.search_for(phrase):
                    has_link = any(x.get("kind") in (fitz.LINK_GOTO, fitz.LINK_NAMED) and x.get("page", -1) >= 0 and not (region & fitz.Rect(x["from"])).is_empty for x in links)
                    if not has_link:
                        unlinked_here += 1
            if unlinked_here:
                errors.append(f"page {pno+1}: {unlinked_here} numeric citation groups lack GoTo links")
        details.append({
            "page": pno+1, "text_chars": len(text), "images": len(page.get_images(full=True)),
            "drawings": len(page.get_drawings()), "goto_links": goto_here, "named_internal_links": named_here,
            "numeric_citation_groups": len(groups), "unlinked_groups": unlinked_here,
        })
    if replacement:
        errors.append(f"replacement character U+FFFD on pages: {replacement}")
    if citation_groups and (goto + named) == 0:
        errors.append("body contains numeric citation markers but no internal GoTo links")
    if mode == "pdf" and start is None:
        errors.append("PDF bibliography mode requires detectable reference pages or --ref-start-page")
    if mode == "pdf" and not all_refs:
        errors.append("PDF bibliography mode has no numbered bibliography entries")
    if mode == "pdf" and citation_groups == 0:
        warnings.append("no numeric body citations detected; confirm the paper actually has none")
    if mode == "native" and start is None:
        warnings.append("no numbered bibliography start detected; this is okay for author-year citation styles")
    if mode == "native" and citation_groups and (goto + named) < 1:
        errors.append("native LaTeX numeric citations are not linked")
    if all_refs and min(all_refs) != 1:
        warnings.append(f"bibliography numbering begins with [{min(all_refs)}]")
    doc.close()
    result = {
        "pdf": str(pdf), "mode": mode, "pages": len(details),
        "reference_start_page": start+1 if start is not None else None,
        "reference_numbers": sorted(all_refs), "citation_groups": citation_groups,
        "goto_links": goto, "named_internal_links": named, "internal_links": goto + named, "uri_links": uri,
        "fonts_by_page": dict(fonts.most_common()), "warnings": warnings,
        "errors": errors, "page_details": details,
    }
    # No silent pass with a broken citation path when --strict is selected.
    if strict and errors:
        return result
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--mode", choices=["native", "pdf"], default="native")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ref-start-page", type=int)
    args = ap.parse_args()
    info = audit(args.pdf, args.mode, args.strict, args.ref_start_page)
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        print(f"PDF: {info['pages']} pages; {info['citation_groups']} citation groups; {info['internal_links']} internal links; {info['uri_links']} URLs")
        print("Embedded font names: " + ", ".join(info["fonts_by_page"]))
        for warn in info["warnings"]: print("WARN: " + warn)
        for err in info["errors"]: print("ERROR: " + err)
        print("PDF audit: " + ("FAILED" if info["errors"] and args.strict else "COMPLETE"))
    if info["errors"] and args.strict:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
