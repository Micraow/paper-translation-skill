#!/usr/bin/env python3
"""Run latexmk while keeping verbose TeX output on disk, not in agent context.

Errors still fail the build. The full console output remains in
work/latexmk-console.log and the structured TeX log remains in build/main.log.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

PROBLEM = re.compile(
    r"^! |(?:(?:\.tex|\.sty|\.cls):\d+:)|"
    r"(?:Package .* Error:|LaTeX Error:|Fatal error|Emergency stop|"
    r"Missing character:|Undefined control sequence|Citation .* undefined|"
    r"Reference .* undefined|Latexmk: Errors,|Collected error summary)",
    re.I,
)


def diagnostics(output: str, limit: int = 15) -> tuple[list[str], int]:
    selected = []
    for line in output.splitlines():
        stripped = line.strip()
        if PROBLEM.search(stripped):
            if stripped not in selected:
                selected.append(stripped)
    return selected[:limit], max(0, len(selected) - limit)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--main", default="main.tex")
    ap.add_argument("--build-dir", default="build")
    ap.add_argument("--log", type=Path, default=Path("work/latexmk-console.log"))
    ap.add_argument("--latexmk", default="latexmk", help="executable (useful for tests)")
    ap.add_argument("--verbose", action="store_true", help="also echo entire stdout, for interactive debugging")
    args = ap.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [args.latexmk, "-xelatex", f"-outdir={args.build_dir}", args.main]
    try:
        result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, errors="replace", check=False)
    except FileNotFoundError as exc:
        ap.exit(127, f"ERROR: {exc}\n")
    args.log.write_text(result.stdout, encoding="utf-8")
    if args.verbose:
        print(result.stdout, end="\n" if not result.stdout.endswith("\n") else "")
    if result.returncode:
        problems, remaining = diagnostics(result.stdout)
        print(f"XeLaTeX build FAILED (exit={result.returncode}); full console log: {args.log}")
        for line in problems:
            print("  " + line[:360])
        if remaining:
            print(f"  ... {remaining} more distinct diagnostics; inspect full log")
        if not problems:
            print("  Last lines:")
            for line in result.stdout.splitlines()[-8:]:
                print("  " + line[:360])
        ap.exit(result.returncode)
    pdf = Path(args.build_dir) / Path(args.main).with_suffix(".pdf").name
    if not pdf.is_file():
        ap.exit(2, f"ERROR: latexmk exited 0 but expected PDF not found: {pdf}. Full log: {args.log}\n")
    print(f"XeLaTeX OK: {pdf}; full console log: {args.log}")


if __name__ == "__main__":
    main()
