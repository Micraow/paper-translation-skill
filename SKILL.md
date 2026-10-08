---
name: paper-translation
description: Translate a scholarly PDF into a complete, elegant Chinese reading edition in XeLaTeX, preserving equations, vector figures, data, untouched algorithm pseudocode, original bibliography, and working cross-references. Use when a user requests a faithful full-paper translation or publication-quality bilingual-to-Chinese PDF re-typesetting.
---

# Paper Translation — loss-aware research PDF translation and typesetting

Your job is **not** to summarize a paper or to render its pages as screenshots. Deliver a *traceable, full-length Chinese scholarly reading edition* with original scientific meaning, properly embedded figures, searchable text, meaningful hyperlinks, and a reproducible LaTeX project. The original PDF—not extracted plain text or online summaries—is the source of truth.

The included generic XeLaTeX design favors a quiet, spacious style: Latin Modern Roman for western body text where installed, serif CJK text, restrained typography, stable mathematical typesetting, captions and margins with breathing room. When the user supplies their own template, **use it without globally modifying it**; document local overrides only when needed.

## Non-negotiable content contract

Unless the user explicitly requests exceptions:

1. Translate **everything** that is prose: paper title, abstract, main text, section headings, footnotes, acknowledgements, captions, table headers, appendix text, limitations, and notes. Maintain the author's structure, order and strength of claims.
2. Keep **algorithms, pseudocode and source code in the source language**, in the original layout when feasible. Never “fix” code as part of translation.
3. Preserve all figures, tables, measurements, units, graph scales, error bars, equations and original numbering. Never silently invent or normalize numbers.
4. **Retype equations** in semantic LaTeX with `\label{eq:...}` and `\eqref`. Keep **automatic equation numbers whenever they already match** the source; use `\tag{n}` only for a genuine mismatch, checking for duplicate PDF destination warnings. Verify every symbol visually against the source.
5. Prefer **native image extraction or vector-preserving PDF crops** to screenshots. Keep plot-internal annotations in their original language unless the user wants redrawing; translate captions and surrounding discussion.
6. Maintain **clickable in-text references** to bibliography, figures, tables, sections and equations. Native LaTeX citation/ref machinery is the first choice. Where original bibliography pages must be preserved, the included postprocessor reconstructs numeric links.
7. Track all meaningful source text blocks in a **coverage ledger**. A green ledger is required but **not sufficient**: compare translated prose back to the rendered original to catch column-order errors, missing math in paragraphs, and false translations.
8. Do **not** include font binaries, unrelated user data, original unpublished material in the public skill, or copyrighted input PDFs in distributable source archives without permission.

## Set up and prerequisites

Resolve `<skill-dir>` to the directory containing this file. Required: Python 3.10+, PyMuPDF, Pillow, XeLaTeX, `latexmk`, the TeX packages used by `assets/latex-template/paper-translation.sty`, and fonts for CJK typesetting. `pip install -r <skill-dir>/requirements.txt` supplies only the Python dependencies; TeX is separately installed.

```bash
python3 <skill-dir>/scripts/init_project.py /work/translation
cp /path/to/paper.pdf /work/translation/sources/original.pdf
cd /work/translation
```

Always keep the source PDF unchanged, ideally record its SHA-256. The project is independent and rebuildable; source extraction scripts are copied into it.

## Token-aware execution (default, without lost coverage)

**Progressive disclosure:** read this `SKILL.md` once, then load only the phase-specific `references/*.md` needed. Store complete PDF extracts, images, ledger and state **on disk**, never paste them into every model turn. After `seed_coverage.py`, use `make packets` and open `work/context-packets/index.md` plus **one section packet**, glossary matches and relevant original rendered pages; inspect equations, plots, column joins and dubious glyphs visually. For a resumed section, use `prepare_section_packets.py --pending-only --target sections/XX.tex`. The packetizer checks ID completeness but **never approves** coverage rows.

After each verified section, save `.tex`, glossary, crop manifest and reviewed ledger; the next turn uses these artifacts, not entire prior chats. `make` prints bounded build diagnostics and stores the complete log at `work/latexmk-console.log`. Never skip `make release`, bibliography links or final page-by-page source comparison. Do not shorten translated prose/appendices just to save tokens. Prompt caching / cheaper models are optional provider-dependent decisions, not correctness guarantees. See `references/TOKEN_EFFICIENCY.md` **only when needed**.

## Workflow — do not skip phases

### Phase 1 · Inventory the exact source

```bash
python3 scripts/inspect_pdf_assets.py sources/original.pdf
python3 scripts/render_pdf.py sources/original.pdf work/source-render --contact-sheet
python3 scripts/extract_text_blocks.py sources/original.pdf \
  --tsv work/source-blocks.tsv
# Create a paper-specific assets/coverage-map.json using rendered source headings.
cp assets/coverage-map.example.json assets/coverage-map.json
```

Read the **rendered pages** in reading order, not blindly the `get_text()` order. For multi-column layouts, follow each column to its actual end; handle spanning figures and mid-paragraph page transitions. Inventory title metadata, every section, footnote, numbered equation, figure/subfigure, table, algorithm, inline formula, bibliography entry, appendix, and graphical label. Record numbered-asset counts and locations; consider a table in `work/inventory.md` and terminology decisions in `work/glossary.tsv`.

**Do not progress if source content is unreadable, missing pages, or the PDF is encrypted and cannot be read.** Resolve the input problem rather than hallucinating.

See `references/WORKFLOW.md`.

### Phase 2 · Translate all content, maintain traceability

**First seed candidate coverage mappings:** edit `assets/coverage-map.json` to list **all** source headings, ordered and regex-anchored; set the two-column boundary in PDF points. Populate `assets/regions.json` after planning vector crops. Then run:

```bash
python3 scripts/seed_coverage.py work/source-blocks.tsv \
  --headings assets/coverage-map.json --regions assets/regions.json \
  --project-root . --output work/coverage.tsv
```

The seeder **requires every source heading to match exactly once in order** and leaves all statuses `todo`. Its target/status suggestions are not evidence of translation. Generate compact source packets for the **next** section instead of repeatedly passing the entire original to the agent:

```bash
make packets  # produces work/context-packets/index.md + index.json and per-section .md files
# Or just the pending Introduction blocks when resuming:
python3 scripts/prepare_section_packets.py --pending-only \
  --target sections/01-introduction.tex --out-dir work/pending-packets
```

Open the relevant packet and inspect its referenced original rendered pages; inspect formulas/figures visually, because PDF-extracted symbols can be wrong. **No packet marks a ledger row reviewed.** Process the paper *section by section*: compare each source paragraph with the rendered original, translate into the corresponding `sections/*.tex`, and mark the reviewed rows. To confirm a reviewed section in one operation:

```bash
python3 scripts/confirm_coverage.py work/coverage.tsv --status translated \
  --target sections/01-introduction.tex \
  --review-note 'Compared every source block on pages 2-3 with the translated section'
```

Always inspect the suggested rows before signing off; never confirm large unreviewed groups. Read `references/COVERAGE_LEDGER.md` for geometry/heading mapping, preserved assets, font-garbled text, and page-level review commands. Coverage statuses are:

- `translated` — Chinese translation exists; `target_file` points to the relevant real file.
- `preserved` — deliberate verbatim preservation (algorithm/bibliography; record target asset).
- `nonprose` — verified repeated page furniture/decorative blocks only; leave `target_file` empty. Equations are not automatically disposable!
- `skip-with-reason` — a genuine duplicate/artifact with a specific reason in `notes`.
- `todo` — never allowed for final delivery.

Take particular care with **modals** (`may`/`can`/`must`), negations, causal direction, quantifiers, percentiles, orders of magnitude, `Gbps` vs `GB/s`, `$q(k)$` vs `$q_v(k)$`, and citation placement. Introduce technical terms bilingually once and use consistent abbreviations. Do not insert your own analysis into translated body text. Read `references/TRANSLATION_GUIDE.md` and `references/PRECISION_TRANSLATION_POLICY.md`.

Check coverage against the original block list before delivery:

```bash
python3 scripts/validate_coverage.py work/coverage.tsv \
  --source-blocks work/source-blocks.tsv --require-nonempty --require-targets --root .
```

An Agent must still read section beginnings/endings and every page/column boundary; ledger IDs cannot prove a translation is true.

### Phase 3 · Recover graphics without losing vector information

Use the visual decision tree:

| Original graphic type | Correct treatment |
|---|---|
| Single embedded bitmap / photograph | `scripts/extract_embedded_images.py` (original pixels) |
| Vector chart, diagram, vector/raster mixed | `scripts/extract_vector_regions.py` (PDF-to-PDF clipping, preserving searchable text and paths) |
| Simple data table | Native LaTeX `tabularx`, `longtable`, etc.; transcribe/verify each value |
| Complex table with fragile visual details | Preserve as original vector block and translate caption/notes separately (explain retained headings) |
| Algorithm/pseudocode | Keep source content unchanged, preferably original vector crop |
| Scanned/unextractable content | Raster crop only as documented last resort, generally 300+ DPI |

For vector regions:

```bash
python3 scripts/annotate_page_grid.py sources/original.pdf 6 work/grid-page-6.png
# Inspect boundaries, then edit assets/regions.json (page is 1-based, bbox is PDF points).
python3 scripts/extract_vector_regions.py assets/regions.json \
  --preview-dir work/asset-previews
```

Check every crop, especially first/last tick, vertical labels, legends, arrowheads, subfigure lettering and adjacent charts. **Never crop a multi-panel figure by guessing from plain text extraction.** Inspect at full size and after insertion into the final page. See `references/FIGURES_AND_ALGORITHMS.md`.

### Phase 4 · Semantic LaTeX, not merely pretty text

- Store source-order chapters in `sections/` and keep original headings/numbering.
- Figures: vector PDF `\includegraphics`, native translated `\caption`, and `\label{fig:...}` immediately after caption. Refer with `\ref`.
- Equations: `equation`/`align`, original numbering by default, `\tag` **only if auto-numbering differs**, `\label`, `\eqref`. Avoid duplicate `equation.n` PDF anchors.
- Tables: exact values, units, headers, notes; `\caption`, `\label` and `\ref`.
- Sections: `\label{sec:...}` and `\ref`, avoid hard-coding numbers that may move.
- Algorithms: include original code unchanged, **with an independent algorithm counter** (not `figure`, and not `\caption*` + `\label`). Bundled template provides the `algorithm` float and `\numberedpreservedalgorithm[width]{file}{label}` for crops including their original numbered heading; `\translatedalgorithm[width]{body.pdf}{translated caption}{label}` for body-only crops. Refer with `算法~\ref{alg:...}`. Local/custom user templates can declare `\newfloat{algorithm}{htbp}{loa}` in the project preamble rather than modifying a user-owned global `.sty`.
- Units: use `\qty{5.4}{\micro\second}` or the template's `\us` macro. **Never** use `\mathrm{\mu}` for microseconds under `unicode-math` (can request U+1D707 from Latin text font and produce a missing glyph).
- Typography: Chinese `\emph{...}` may silently lose emphasis because many CJK fonts lack italics. The default LaTeX project gate **rejects** literal CJK `\emph`; the log gate also rejects missing italic/small-caps font faces. Use `\zhstrong{...}` / `\textbf{...}` and check the render. An expert can explicitly opt out only after verifying a real CJK italic face. Latin small caps are enabled by the bundled Latin Modern Caps OpenType face.
- Links: `hyperref` loads in the bundled template. Never duplicate-load it if integrating another style; keep the style compatible.

See `references/LATEX_CROSSREFERENCES.md`. Run `scripts/check_latex_project.py` early: it **recursively follows `\input` and `\include`**, catches unresolved labels, missing citation keys and suspicious hard-coded numeric citations in native mode.

### Phase 5 · Choose exactly ONE bibliography backend

**Preferred: `native` (default).** Preserve the complete original bibliography entries in `sections/references.tex` using `\bibitem`/available `.bib` data. Preserve source numbering/order. Cite with `\cite{...}`; LaTeX generates PDF navigation and the project linter checks that keys exist. Do **not** type `[7, 11]` as plain text in this mode.

**Alternative: `pdf` (for a source whose reference pages are best preserved verbatim).** Set `\OriginalReferencePages` in `main.tex` to the source-PDF page range, retain visible numeric `[n]` body citations in the translation, and build with `make BIB_MODE=pdf`. Original PDF pages stay vector; the automatic reference-link restorer attaches internal GoTo links to visible numbers and **fails in strict mode** when a target/printed citation is missing. Use `REF_START_PAGE=<n>` when the *final compiled PDF* bibliography start cannot be detected unambiguously. Do not mix `\cite` with this backend.

```bash
make                          # preferred native references, built-in QA
# or:
make BIB_MODE=pdf              # preserved original bibliography + verified links
```

The default `make` does **not** silently disable citation links. A returned non-zero status is a blocker. See `references/REFERENCES_AND_LINKS.md`.

### Phase 6 · Run production gates AND verify page renders

```bash
make                         # compile + LaTeX recursion/lint + log/PDF/link audit
make release                 # additionally validate complete coverage + render contact sheet
```

`make release` depends on filled `work/source-blocks.tsv` and `work/coverage.tsv`. Then **visually inspect** the contact sheet and full-size pages containing long equations, narrow tables, graphics, algorithms, acknowledgements, bibliography transition, and appendices. Compare source and target side by side. Rebuild until problems are fixed.

Reject: clipped panels, missing paragraphs, overlapping floats, misplaced equations, blank pages, illegible source plots, black squares, lost footnotes, unresolved `\cite`/`\ref`, broken citations, or suspicious typeface substitutions. Confirm PDF text is searchable and every original source section exists.

See `references/QA_CHECKLIST.md`; green automated checks must never be marketed as evidence of semantic correctness.

### Phase 7 · Deliver a reproducible project

Provide (1) finished full translation PDF; (2) editable XeLaTeX project with translated `.tex`, `.sty`, extracted graphics, region manifest, scripts and instructions. Document build command and exceptions taken. Do not include source publication PDF or its graphics in **public skill repository** merely because it was attached to a conversation; confirm redistribution rights first. Do not include user's identity or proprietary fonts unless explicitly wanted in the *user-specific output*.

## Failure recovery

- `pdfimages` returns only tiny icons for a chart → figure is vector/mixed: use PDF-to-PDF clipping.
- `\cite` prints a number but audit claims no GoTo → remember XeLaTeX often stores **named internal destinations**; audit both `LINK_GOTO` and `LINK_NAMED`.
- Citation links replicate across unrelated pages → shared `/Annots` reference from an earlier PDF transform; link-restoration script privatizes those arrays before insertion.
- Script cannot identify references → specify final-PDF bibliography page range; do not guess.
- Fonts differ between machines → pin approved fonts in document/local style, note installed-font dependencies; never distribute font binaries.
- `Missing character ... U+1D707` with `\mathrm{\mu}` → use `\qty{...}{\micro\second}`, `\si{\micro\second}` or `\us`; never change the scientific quantity.
- `\caption*` then undefined `\ref` for algorithm → a star caption does not advance a counter. Use `algorithm` float with `\caption`/`\label`, or `\numberedpreservedalgorithm` for a full original crop.
- `xdvipdfmx ... Object @equation.1 already defined` → check unnecessary `\tag`, maintain unique link destination names; inspect `pymupdf.Document.resolve_names()` and click representative equation links.
- CJK `\emph`/Latin `\textsc` font-shape warnings → restore visible emphasis or use Latin Modern Caps; do not dismiss them as harmless cosmetic logs.
- Hundreds of `todo` coverage rows → run `seed_coverage.py` with crop geometry plus a complete source heading map; every heading must be consumed exactly once, then review and confirm by section.
- `pdftex.map` / `kanjix.map` warning from xdvipdfmx → usually incomplete optional TeX font-map configuration; if output fonts and glyphs are correct it is an environment warning, not a reason to rewrite the paper.
- Formula or cropped graphic looks wrong → return to the rendered source, correct source/clip, render again; don't improvise scientific content.
- Incomplete ledger or unresolved references → **stop**, do not claim a finished full translation.

## Public repository boundary

This MIT-licensed skill contains **methods, scripts and a generic LaTeX template**; it is not a license for third-party source papers, screenshots of those papers, proprietary fonts, or user-provided texts. Read `THIRD_PARTY_NOTICES.md` before reusing promotional screenshots.
