#!/usr/bin/env python3
"""Initialize a self-contained academic-paper translation project."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    template = skill_root / "assets" / "latex-template"
    dest = args.destination.resolve()

    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"Destination exists and is not empty: {dest}")
    dest.mkdir(parents=True, exist_ok=True)

    # Copy template contents, preserving any pre-created empty destination.
    for item in template.iterdir():
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)

    # Carry required Python dependencies and the tool license with the project.
    # A cloned project remains buildable even after the skill directory is moved.
    for filename in ("requirements.txt", "LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(skill_root / filename, dest / filename)

    out_scripts = dest / "scripts"
    out_scripts.mkdir(exist_ok=True)
    for script in (skill_root / "scripts").glob("*.py"):
        if script.name == "init_project.py":
            continue
        shutil.copy2(script, out_scripts / script.name)

    print(f"Initialized project: {dest}")
    print("Next: place the source PDF at sources/original.pdf")


if __name__ == "__main__":
    main()
