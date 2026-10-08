#!/usr/bin/env python3
"""Fail on common LaTeX production warnings that should block delivery."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

PATTERNS = {
    "latex_error": re.compile(r"^! ", re.M),
    "undefined_references": re.compile(r"(There were undefined references|Reference `[^']+' .* undefined)", re.I),
    "undefined_citations": re.compile(r"Citation `[^']+' .* undefined", re.I),
    "missing_character": re.compile(r"Missing character:", re.I),
    "font_shape_substitution": re.compile(
        r"LaTeX Font Warning: Font shape [`']?[^\n]*?/(?:it|sc)['`]? undefined", re.I
    ),
    "overfull_hbox": re.compile(r"Overfull \\hbox", re.I),
    "overfull_vbox": re.compile(r"Overfull \\vbox", re.I),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("log", type=Path)
    ap.add_argument("--allow-overfull", action="store_true")
    ap.add_argument("--allow-font-substitutions", action="store_true",
                    help="unsafe unless each substituted font face was visually reviewed")
    args = ap.parse_args()

    text = args.log.read_text(encoding="utf-8", errors="replace")
    counts = {name: len(rx.findall(text)) for name, rx in PATTERNS.items()}
    for name, count in counts.items():
        print(f"{name}: {count}")

    blockers = [
        "latex_error",
        "undefined_references",
        "undefined_citations",
        "missing_character",
    ]
    if not args.allow_font_substitutions:
        blockers.append("font_shape_substitution")
    if not args.allow_overfull:
        blockers += ["overfull_hbox", "overfull_vbox"]

    bad = {k: counts[k] for k in blockers if counts[k]}
    if bad:
        print(f"FAIL: {bad}")
        raise SystemExit(1)
    print("LaTeX log OK")


if __name__ == "__main__":
    main()
