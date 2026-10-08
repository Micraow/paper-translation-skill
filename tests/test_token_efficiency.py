"""Context-routing and concise-build regressions; no external LLM/API dependency."""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def write_tsv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def run_script(name, *args, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)],
                          cwd=cwd, capture_output=True, text=True)


class ContextPacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        d = self.d = Path(self.temp.name)
        self.sources = d / "source-blocks.tsv"
        self.ledger = d / "coverage.tsv"
        self.config = d / "map.json"
        self.out_dir = d / "packets"
        rows = [
            ("p001-b003", "1", "3", "340", "110", "490", "160", "Algorithm pseudocode MUST stay English."),
            ("p001-b001", "1", "1", "50", "80", "270", "100", "1 Introduction: deterministic context."),
            ("p001-b002", "1", "2", "50", "110", "270", "150", "Need precise statements " + "x" * 1200),
            ("p002-b001", "2", "1", "40", "80", "260", "160", "2 Results: symbols \ufffd need original rendering."),
            ("p002-b002", "2", "2", "40", "170", "260", "210", "The algorithm improves latency by 12%."),
        ]
        write_tsv(self.sources, ["source_id", "page", "block", "x0", "y0", "x1", "y1", "text"],
                  [dict(zip(["source_id", "page", "block", "x0", "y0", "x1", "y1", "text"], row)) for row in rows])
        ledgers = [
            {"source_id": sid, "source_page": "1" if sid.startswith("p001") else "2",
             "status": "todo", "target_file": "", "notes": "", "source_preview": "",
             "suggested_status": "preserved" if sid == "p001-b003" else "translated",
             "suggested_target": "figures/algorithm01.pdf" if sid == "p001-b003"
                 else ("sections/01-introduction.tex" if sid.startswith("p001")
                       else "sections/02-results.tex")}
            for sid, *_ in rows
        ]
        write_tsv(self.ledger,
                  ["source_id", "source_page", "status", "target_file", "notes", "source_preview",
                   "suggested_status", "suggested_target"], ledgers)
        self.config.write_text(json.dumps({"reading_order": "two-column", "column_split_x": 300}), encoding="utf-8")
        self.glossary = d / "glossary.tsv"
        write_tsv(self.glossary, ["source_term", "translation"], [
            {"source_term": "latency", "translation": "时延"},
            {"source_term": "unrelated", "translation": "不相关"},
        ])

    def gen(self, *additional):
        return run_script("prepare_section_packets.py", "--source-blocks", self.sources,
                          "--ledger", self.ledger, "--headings", self.config,
                          "--glossary", self.glossary, "--out-dir", self.out_dir,
                          *additional)

    def test_all_ids_in_index_without_truncation_or_automatic_approval(self):
        before = self.ledger.read_bytes()
        p = self.gen("--max-chars", "1500")
        self.assertEqual(0, p.returncode, p.stderr)
        idx = json.loads((self.out_dir / "index.json").read_text())
        ids = [sid for entry in idx["entries"] for sid in entry["source_ids"]]
        self.assertEqual(5, len(ids))
        self.assertEqual(5, len(set(ids)))
        self.assertTrue(idx["all_source_blocks_accounted"])
        self.assertEqual(before, self.ledger.read_bytes())  # no fake coverage
        self.assertTrue((self.out_dir / "index.md").exists())
        self.assertIn("Need precise statements " + "x" * 1200, "\n".join(
            f.read_text() for f in self.out_dir.glob("*.md") if f.name != "index.md"))
        intro_parts = [e for e in idx["entries"] if e["target"] == "sections/01-introduction.tex"]
        self.assertGreaterEqual(len(intro_parts), 1)
        self.assertIn("EXTRACTION UNCERTAIN", "\n".join(
            f.read_text() for f in self.out_dir.glob("*.md") if f.name != "index.md"))
        self.assertEqual(1, sum(e["target"] == "figures/algorithm01.pdf" for e in idx["entries"]))
        self.assertIn("latency → 时延", "\n".join(
            f.read_text() for f in self.out_dir.glob("*.md") if f.name != "index.md"))
        self.assertNotIn("unrelated → 不相关", "\n".join(
            f.read_text() for f in self.out_dir.glob("*.md") if f.name != "index.md"))

    def test_resume_only_pending_and_exact_target(self):
        rows = []
        with self.ledger.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f, delimiter="\t"))
        rows[1]["status"] = "translated"
        rows[1]["target_file"] = "sections/01-introduction.tex"
        write_tsv(self.ledger, list(rows[0]), rows)
        p = self.gen("--pending-only", "--target", "sections/01-introduction.tex")
        self.assertEqual(0, p.returncode, p.stderr)
        idx = json.loads((self.out_dir / "index.json").read_text())
        ids = [sid for e in idx["entries"] for sid in e["source_ids"]]
        self.assertEqual(["p001-b002"], ids)
        self.assertEqual(5, sum(idx["all_targets"].values()))
        self.assertEqual(4, sum(idx["pending_by_target"].values()))

    def test_conflicts_and_missing_source_ids_fail_without_overwriting(self):
        self.assertEqual(0, self.gen().returncode)
        index = self.out_dir / "index.md"
        index.write_text("manual notes", encoding="utf-8")
        p = self.gen()
        self.assertNotEqual(0, p.returncode)
        self.assertIn("--force", p.stderr)
        self.assertEqual("manual notes", index.read_text())
        self.assertEqual(0, self.gen("--force").returncode)
        with self.ledger.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f, delimiter="\t"))
        write_tsv(self.ledger, list(rows[0]), rows[:-1])
        p = self.gen("--force")
        self.assertNotEqual(0, p.returncode)
        self.assertIn("mismatch", p.stderr)


class QuietCompileTests(unittest.TestCase):
    def test_bounded_latex_diagnostics_preserved_full_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            fake = d / "failing-latexmk"
            fake.write_text("#!/bin/sh\necho 'Loading package abc'\necho './main.tex:99: LaTeX Error: Undefined control sequence.'\nexit 12\n")
            fake.chmod(0o755)
            p = run_script("run_latexmk.py", "--latexmk", fake, cwd=d)
            self.assertEqual(12, p.returncode)
            self.assertIn("build FAILED", p.stdout)
            self.assertIn("main.tex:99", p.stdout)
            self.assertNotIn("Loading package", p.stdout)
            self.assertIn("Loading package", (d / "work/latexmk-console.log").read_text())

    def test_success_requires_actual_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            fake = d / "successful-latexmk"
            fake.write_text("#!/bin/sh\nmkdir -p build\nprintf 'dummy' > build/main.pdf\necho 'Long success log'\nexit 0\n")
            fake.chmod(0o755)
            p = run_script("run_latexmk.py", "--latexmk", fake, cwd=d)
            self.assertEqual(0, p.returncode, p.stdout + p.stderr)
            self.assertIn("XeLaTeX OK", p.stdout)
            self.assertNotIn("Long success log", p.stdout)


if __name__ == "__main__":
    unittest.main()
