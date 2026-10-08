# Agent translation postmortem: fixes and decisions

This document records practical findings from running the skill on a multi-column systems paper. It describes generic behavior rather than distributing source PDFs or an agent's translated text.

| Symptom | Ownership | Resolution |
|---|---|---|
| `unicode-math`, `\mathrm{\mu}`, U+1D707 missing | Skill typography guidance & preflight | `\us` and `siunitx` examples; static lint with actionable message; integration test for printed µs |
| Preserved Algorithm incorrectly numbered as Figure; `\caption*` makes `\ref` undefined | Missing template capability | Independent `algorithm` float, `\numberedpreservedalgorithm` for original-heading crops, `\translatedalgorithm` for body-only crops; actual PDF link test |
| `[1]` argument count in `\newcommand` falsely identified as a hard-coded citation | Defect in source scanner | Recognize definition arity *only*, not entire macro-definition lines; keep strict detection of `[7, 11]` prose citations |
| `\tag{n}` may create duplicate PDF named destinations under hyperref | Overstrong documentation advice | Prefer automatic numbering; use `\setcounter` for contiguous offset; reserve `\tag` for irregular numbering and inspect warnings/destinations |
| CJK `\emph` silently loses emphasis; Latin small caps silently substitute | Template/lint quality gap | `\zhstrong`, explicit Latin Modern Caps OpenType face, strict default checks for CJK `\emph` and font shape substitutions |
| Hundreds of manually assigned ledger rows | Missing scale workflow | `seed_coverage.py` proposes geometry-based asset preservation and title-driven section assignments; `confirm_coverage.py` confirms only reviewed groups; exact-once title assertions; overwrite protection |
| Source text C0 controls break TSV viewers | Extraction defect | Printable replacement marker U+FFFD; explicit raw option for debugging; rendered source remains authoritative |
| `pdftex.map` / `kanjix.map` warnings | Environment, not translation | Troubleshooting note only; do not loosen missing-glyph/real QA checks to hide unrelated warnings |

## Important limits

1. A successful LaTeX build proves neither source coverage nor technical translation fidelity.
2. Automated coverage **suggestions** must remain `todo`; a reviewer confirms only blocks they actually compared against the original rendered pages.
3. Reading order in two-column PDFs can still be ambiguous around spanning figures, page transitions and mixed-width headings. The source-heading consumption assertion detects missing titles but does not replace page-by-page review.
4. A `resolve_names()` PDF name tree cannot identify all overwritten duplicate destinations from the compilation stream. Review the `xdvipdfmx` console output and click representative links.
5. Fixes are regression-tested against synthetic inputs and a representative real multi-column PDF. This is not a benchmark of translation accuracy across different LLM agents.
