#!/usr/bin/env python3
r"""Check a multi-file translated-paper LaTeX project for reference errors.

Static scanning complements, but never replaces, a real XeLaTeX build and log audit.
Mode 'native' requires \cite keys resolved by \bibitem or local .bib entries.
Mode 'pdf' allows visible numeric citations because their clickable links are added
and audited after compilation.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

INPUT_RE = re.compile(r"\\(?:input|include|subfile)\s*\{([^{}]+)\}")
LABEL_RE = re.compile(r"\\label\s*\{([^{}]+)\}")
REFERENCE_RE = re.compile(r"\\(?:ref|eqref|autoref|cref|Cref|pageref)\*?\s*\{([^{}]+)\}")
CITE_RE = re.compile(r"\\(?:cite|citep|citet|citealt|citeauthor|parencite|textcite|autocite)\*?(?:\[[^]]*\]){0,2}\s*\{([^{}]+)\}")
BIBITEM_RE = re.compile(r"\\bibitem(?:\[[^\]]*\])?\s*\{([^{}]+)\}")
BIBRESOURCE_RE = re.compile(r"\\(?:addbibresource|bibliography)\s*\{([^{}]+)\}")
BIB_ENTRY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,", re.I)
HARDCODE_RE = re.compile(r"(?<![\w\\])\[(?:[1-9]\d*)(?:\s*[,–-]\s*[1-9]\d*)*\]")


def strip_comments(src: str) -> str:
    """Remove TeX comments, retaining escaped percent signs and line numbers."""
    out = []
    for line in src.splitlines(keepends=True):
        for i, c in enumerate(line):
            if c == "%":
                j = i - 1
                while j >= 0 and line[j] == "\\":
                    j -= 1
                if (i - 1 - j) % 2 == 0:
                    line = line[:i] + ("\n" if line.endswith("\n") else "")
                    break
        out.append(line)
    return "".join(out)


def resolve_tex(name: str, current: Path, root: Path) -> Path | None:
    # TeX normally resolves from the main working directory; fallback to relative
    # include paths for projects that deliberately use nested local directories.
    item = Path(name)
    if item.suffix == "":
        item = item.with_suffix(".tex")
    for p in (root / item, current.parent / item):
        if p.is_file():
            return p.resolve()
    return None


def collect(main: Path) -> tuple[dict[Path, str], list[str]]:
    root = main.parent.resolve()
    visited: dict[Path, str] = {}
    errors: list[str] = []

    def visit(path: Path) -> None:
        path = path.resolve()
        if path in visited:
            return
        if not path.is_file():
            errors.append(f"missing LaTeX file: {path}")
            return
        cleaned = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        visited[path] = cleaned
        for name in INPUT_RE.findall(cleaned):
            if "\\" in name or "#" in name:
                # Dynamic paths cannot be resolved reliably by a static check.
                errors.append(f"cannot statically resolve input in {path.name}: {name}")
                continue
            target = resolve_tex(name, path, root)
            if target is None:
                if re.search(r"\\IfFileExists\s*\{" + re.escape(name) + r"\}", cleaned):
                    continue
                errors.append(f"unresolved input in {path.name}: {name}")
            else:
                visit(target)

    visit(main)
    return visited, errors


def check(main: Path, mode: str, require_citations: bool = False) -> dict:
    files, errors = collect(main)
    warnings: list[str] = []
    full = "\n".join(files.values())
    labels = LABEL_RE.findall(full)
    refs = [x.strip() for group in REFERENCE_RE.findall(full) for x in group.split(",")]
    cites = [x.strip() for group in CITE_RE.findall(full) for x in group.split(",")]
    bibkeys = set(BIBITEM_RE.findall(full))
    bibfiles: list[str] = []
    for group in BIBRESOURCE_RE.findall(full):
        for part in group.split(","):
            name = part.strip()
            p = Path(name if name.endswith(".bib") else f"{name}.bib")
            # Most projects place .bib next to main; relative fallback is intentional.
            bpath = (main.parent / p).resolve()
            bibfiles.append(str(bpath))
            if not bpath.is_file():
                errors.append(f"missing bibliography resource: {p}")
            else:
                bibkeys.update(BIB_ENTRY_RE.findall(bpath.read_text(encoding="utf-8", errors="replace")))
    duplicates = [key for key, count in Counter(labels).items() if count > 1]
    duplicate_bibs = [key for key, count in Counter(BIBITEM_RE.findall(full)).items() if count > 1]
    if duplicates:
        errors.append(f"duplicate labels: {sorted(duplicates)}")
    if duplicate_bibs:
        errors.append(f"duplicate bibitems: {sorted(duplicate_bibs)}")
    unknown_refs = sorted(set(refs) - set(labels))
    if unknown_refs:
        errors.append(f"unresolved figure/equation/section labels: {unknown_refs}")
    if mode == "native":
        unknown_cites = sorted(set(cites) - bibkeys)
        if unknown_cites:
            errors.append(f"unresolved citation keys: {unknown_cites}")
        hardcoded = []
        for path, src in files.items():
            for n, line in enumerate(src.splitlines(), 1):
                if HARDCODE_RE.search(line) and not line.lstrip().startswith("\\bibitem"):
                    hardcoded.append(f"{path.name}:{n}")
        if hardcoded:
            errors.append("possible hard-coded numeric citations in native mode: " + ", ".join(hardcoded[:12]))
    elif cites:
        errors.append("PDF-bibliography mode should use literal numbered citations; remove LaTeX \\cite commands")
    if require_citations and mode == "native" and not cites:
        errors.append("native mode expected at least one \\cite")
    if mode == "native" and not bibkeys:
        warnings.append("no bibliography keys found (sample or unfinished project?)")
    return {
        "main": str(main), "mode": mode, "tex_files": [str(p) for p in files],
        "labels": len(labels), "label_references": len(refs), "citation_calls": len(cites),
        "bibliography_keys": len(bibkeys), "bibliography_files": bibfiles,
        "errors": errors, "warnings": warnings,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("main", type=Path)
    ap.add_argument("--mode", choices=("native", "pdf"), default="native")
    ap.add_argument("--require-citations", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    result = check(args.main.resolve(), args.mode, args.require_citations)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Inspected {len(result['tex_files'])} TeX files; {result['labels']} labels, {result['citation_calls']} citation calls")
        for line in result["warnings"]: print(f"WARN: {line}")
        for line in result["errors"]: print(f"ERROR: {line}")
        print("LaTeX project check: " + ("FAILED" if result["errors"] else "OK"))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
