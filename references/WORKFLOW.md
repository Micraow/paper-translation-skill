# End-to-End Workflow

This document expands the operational sequence in `SKILL.md`.

## Phase A — Source reconnaissance

Before translation, build a structural map of the paper from **both parsed text and rendered pages**.

Record at minimum:

| Item | What to record |
|---|---|
| Metadata | title, authors, affiliations, venue/year, corresponding-author footnote |
| Front matter | abstract start/end, keywords if any |
| Hierarchy | section/subsection/subsubsection titles in order |
| Equations | equation numbers and approximate source page |
| Figures | figure number, source page, whether crop must exclude caption |
| Tables | table number, source page, re-typeset vs preserve visually |
| Algorithms | algorithm number, source page, preserve verbatim by default |
| Footnotes | exact attachment point |
| Appendices | appendix labels/titles/order |
| References | first/last reference page, numbering style |
| Hyperlinks | whether original body citations are clickable |

### Why rendered pages are mandatory

Academic PDFs often use two columns, floating figures, footnotes, and text boxes. Text extraction may interleave columns or place a figure caption before the prose that visually precedes it. Never infer section boundaries or paragraph order solely from extracted text.

## Phase B — Coverage mapping

Run `extract_text_blocks.py` to index the source into a TSV. **Do not hand-map hundreds of PDF blocks one at a time.** Use `seed_coverage.py` with a visually verified source-heading map (`assets/coverage-map.json`) and the `regions.json` crop manifest. For two-column papers provide `column_split_x` and list every source section heading in order. The seeder **refuses** to write a ledger if any heading is missed, duplicated, or out of order. It fills `suggested_status` / `suggested_target` but leaves all entries `todo`; only a reviewed source-to-translation comparison can finalize them. Use `confirm_coverage.py` to accept a *reviewed* section as one group, with a review note and actual target. See [COVERAGE_LEDGER.md](COVERAGE_LEDGER.md) for commands and safeguards.

Recommended source IDs stay stable throughout the project:

- `p002-b004` — page 2, extracted block 4;
- for manually split blocks, append `.a`, `.b`;
- for a merged paragraph spanning blocks, list both IDs in the notes.
- text extracted with replacement glyphs or wrong math symbols is only a location hint; translate from the rendered page, not the TSV.

The coverage ledger is not a translation memory. It is a **completeness proof aid**.

### Important boundary checks

Pay special attention to:

- bottom of left column -> top of right column;
- page breaks inside a sentence;
- text immediately after a displayed equation;
- prose above/below figures;
- continuation after a bullet list;
- author footnotes near the first page;
- appendix continuation pages.

These are the most common places for accidental sentence loss.

## Phase C — Terminology pass

Before doing the final prose pass, create a small terminology table in working notes:

| Source term | Chinese translation | Abbreviation | Notes |
|---|---|---|---|
| congestion information deduction | 拥塞信息推断 | CiD | Keep abbreviation |
| delay ambiguity condition | 时延歧义条件 | DAC | Keep abbreviation |

Keep the table project-local; do not inject it into the PDF unless useful.

## Phase D — Translation pass

Translate section-by-section, but use source-page renders while working. Preserve the paper's rhetorical structure.

A good sequence is:

1. abstract;
2. introduction;
3. background/related preliminaries;
4. motivation/analysis;
5. design/method;
6. implementation;
7. evaluation;
8. related work;
9. conclusion;
10. acknowledgements and appendices.

For each section:

1. translate all prose;
2. re-typeset equations;
3. insert figure/table/algorithm placeholders;
4. mark coverage rows complete;
5. compile periodically to catch LaTeX issues early.

## Phase E — Asset extraction

### Prefer source-native assets

Use this order:

1. embedded raster extraction, if the figure is one actual image object;
2. vector PDF region crop, if the figure is assembled from vector/text/multiple objects;
3. screenshot/raster crop only if the source itself is a scan or no native extraction can preserve the visual.

### Crop discipline

Crop the **figure body** rather than the whole surrounding column whenever the caption will be translated separately.

For each crop check:

- x/y axes fully visible;
- legend fully visible;
- all line labels visible;
- no neighboring body text included;
- no original caption included unless deliberately preserved;
- no hairline border lost at the crop edge.

Allow a small safety margin around the figure. Vector PDF crops cost almost nothing in quality.

## Phase F — LaTeX production

Use the provided style as a starting point, not as a reason to override the paper's content hierarchy.

### Page architecture

Recommended translated-paper layout:

- cover/title page;
- translator/editorial note explaining what is translated vs preserved;
- paper metadata;
- optional original first page for provenance;
- translated abstract;
- translated body;
- appendices;
- original bibliography pages or re-typeset bibliography.

### Section numbering

Follow the paper. If the source uses numbered sections, use numbered LaTeX sections. If the source has unnumbered acknowledgements/references, preserve that distinction.

### Equations

Use native LaTeX math. **First try automatic equation numbering** with `\label` and `\eqref`; if it already matches the source, do not add `\tag`. When numbers start at an offset, `\setcounter{equation}{<previous>}` is generally safer than individually tagging every equation. Only if an individual original equation number cannot otherwise be preserved, use an explicit tag:

```tex
\begin{equation}
  q(k)=RTT(k)-RTT_{\min}.
  \tag{2}\label{eq:queue}
\end{equation}
```

Never renumber equations silently. `\tag` combined with `hyperref` can produce duplicate named-destination warnings such as `Object @equation.1 already defined`; remove unnecessary tags first, then audit final PDF destinations using `pymupdf.open(...).resolve_names()` and manually sample the clickable links.

### Algorithm floats and text styles

Use the bundled `algorithm` float rather than `figure` when an original Algorithm has a number or a cross-reference. If the crop includes the original "Algorithm n" heading, use `\numberedpreservedalgorithm{figures/alg.pdf}{alg:...}`. If the crop contains only code, use `\translatedalgorithm{figures/alg-body.pdf}{中文标题}{alg:...}`. `\caption*` does not create a reference anchor. Never duplicate the source's visible algorithm heading with a new caption.

Use `\qty{5.4}{\micro\second}` / `5.4\,\us` rather than `\mathrm{\mu s}`: `unicode-math` can yield a missing U+1D707 glyph. For Chinese emphasis, use `\zhstrong{文字}` instead of relying on italic `\emph{中文}` with a non-italic CJK font. Latin small caps work with the included Latin Modern Caps face.

## Phase G — Bibliography strategy

Choose one mode.

### Mode 1: Re-typeset bibliography

Best if a reliable BibTeX/BibLaTeX source exists. Use normal citation commands and `hyperref`; links come for free.

### Mode 2: Preserve original bibliography pages

Best when exact bibliographic fidelity matters or no clean `.bib` exists.

- import original bibliography pages using `pdfpages`;
- keep entries untouched;
- run `add_reference_links.py` after LaTeX compilation to add internal GoTo annotations from translated citations.

This is the default template strategy.

## Phase H — QA

There are two independent QA tracks.

### Semantic QA

- coverage ledger complete;
- no missing paragraphs/sentences;
- no claim strengthened/weakened;
- variable names and units unchanged;
- figure/equation references match source;
- terminology consistent.

### Production QA

- render every page;
- inspect contact sheet;
- zoom figure/algorithm/equation pages;
- check links;
- inspect fonts;
- parse LaTeX log;
- rebuild from clean state.

A PDF can pass one track and fail the other. Both are required.
