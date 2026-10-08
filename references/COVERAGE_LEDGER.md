# Practical source-coverage ledger at paper scale

The ledger is **traceability**, not a translation-quality score. A 15-page, two-column PDF may generate 800+ extracted blocks. Do not require an agent to hand-enter hundreds of repetitive paths, but **never mark machine suggestions as verified translations** merely because every source ID has a row.

## 1. Extract source blocks (IDs are stable)

```bash
python3 scripts/extract_text_blocks.py sources/original.pdf \
  --tsv work/source-blocks.tsv
```

The exporter replaces invalid C0 PDF glyph mappings with the visible replacement character `�` (U+FFFD). This keeps TSVs readable; it does **not** repair the original content. Some fonts also extract valid-but-wrong Unicode characters. Treat `text`/`source_preview` strictly as **location aids**. Read the rendered source PDF to translate formulae, typography and scientific symbols. `--keep-raw` is available only for extraction debugging and may produce text unreadable by other tools.

## 2. Prepare a heading map *from rendered pages*

Copy `assets/coverage-map.example.json` to `assets/coverage-map.json` (the latter contains paper-specific headings). Edit:

- `headings`: exact source headings **in document order**. Each `match` is a Python regex searched against normalized extracted blocks; each has the corresponding project-relative `target_file`. For example `^3\\s+Design\\b` → `sections/03-design.tex`. Add a references heading with `"status": "preserved"` if references are retained verbatim.
- `reading_order`: set `"two-column"` for a two-column source; specify the exact column boundary in **PDF points** as `column_split_x`. Use grid overlays or original PDF geometry to choose it; **do not guess**. For a single column, use `"source"`.
- `default_target`: where front matter goes before the first heading, if any.
- `furniture_patterns`: narrow anchored regexes for genuine repetitive page furniture; do not classify first-page footnotes, copyright/licensing statements, or actual scientific prose as ignorable merely because they appear low on the page.
- `caption_patterns`: caption matching hints. Figures with vector crops should have an entry in `assets/regions.json`, optionally `"kind": "algorithm"` or `"kind": "figure"`. The tool can suggest `preserved` with the extracted PDF file as its target.

**Critical assertion:** all configured source headings must match **exactly once and in order**. If any title is missed or repeated, the tool exits nonzero without writing a new ledger. Otherwise, a missed heading can silently mis-map all subsequent text blocks to the preceding section.

## 3. Generate candidate mappings (all unreviewed)

```bash
python3 scripts/seed_coverage.py work/source-blocks.tsv \
  --headings assets/coverage-map.json \
  --regions assets/regions.json \
  --project-root . \
  --output work/coverage.tsv
```

A successful run fills `suggested_status`, `suggested_target`, and `suggestion_reason`, while leaving **every `status` as `todo`**. This is intentional: geometric overlap and regex matches cannot prove that an extracted paragraph has been faithfully translated, a caption was not omitted, or a crop is complete. A block intersecting multiple vector regions or an out-of-order heading stops generation for correction.

The ledger distinguishes:

| Status | Meaning | `target_file` |
|---|---|---|
| `translated` | Reviewed Chinese text or faithfully re-typeset equation | Existing `sections/*.tex` |
| `preserved` | Reviewed original algorithm, chart labels, bibliography or other verbatim content | Existing `figures/*.pdf` or reference `.tex` |
| `nonprose` | Only repeated page furniture/decorative or non-independent content, verified against source | **Empty** |
| `skip-with-reason` | Duplicate/extraction garbage, backed by specific notes | Usually empty; a real omission is NOT a valid reason |
| `todo` | Anything not individually/group reviewed | Empty |

For an isolated equation, classify it as `translated` with its actual `.tex` target or `preserved` with its image target, **not** `nonprose` just because it is not natural-language prose. First-page author notes and citation data still count as meaningful content.

## 4. Review by source section/page and confirm groups

For each chapter, read the original page renders, compare every block (including column/page boundaries) with the complete translated `.tex` file, check equations/figures separately, and only then confirm its proposed group:

```bash
python3 scripts/confirm_coverage.py work/coverage.tsv \
  --status translated \
  --target sections/01-introduction.tex \
  --review-note 'Compared source pages 2-4, both columns and end of section'

# For a reviewed algorithm crop:
python3 scripts/confirm_coverage.py work/coverage.tsv \
  --status preserved --target figures/algorithm01.pdf \
  --review-note 'Checked all algorithm lines and original heading against page 7'

# For reviewed non-content footers *on one page*:
python3 scripts/confirm_coverage.py work/coverage.tsv \
  --status nonprose --page 3 \
  --review-note 'Reviewed repeated running footer only on source page 3'
```

Always examine which source blocks the group selection includes before accepting the result. `confirm_coverage.py` only changes bookkeeping and requires an explicit review note; it is **not** an automated semantic review. If a proposal is wrong, manually change that row's `status`, `target_file` and `notes` instead. Do not confirm all rows in bulk without visually comparing source and target.

**Important:** In two-column articles with full-width figures or references in mixed layouts, geometric sort order alone may not reflect true semantic order. If the heading-map assertion fails, correct the order or use smaller source-page sections; do not force an incorrect mapping just to make `make release` green.

## 5. Structural release gate

```bash
python3 scripts/validate_coverage.py work/coverage.tsv \
  --source-blocks work/source-blocks.tsv --require-nonempty --require-targets --root .
make release
```

`validate_coverage.py` checks missing/duplicate block IDs, unfinished TODOs, required reasons, target files and that `nonprose` has an empty target. It cannot inspect Chinese meaning. The agent still must independently check a complete rendered-page contact sheet and the original-to-translation paragraph alignment. A green ledger without this review is a false positive.
