# Token-Efficient Scholarly Translation (Without Dropping Content)

This is an execution guide for agent harnesses. It does **not** relax the skill's full-paper content contract or QA. PDF translation is input/output heavy by nature: every translated word must be produced once and every scientific claim verified. The savings target is duplicate context, not source coverage.

## Why a faithful translation becomes expensive

- Re-sending the same 15+ page PDF or all page images with each request multiplies **input** volume.
- Reading `SKILL.md` and every `references/*.md` repeatedly duplicates instructions.
- Tool stdout from TeX engines, `ls`, `cat` of hundreds of ledger lines, JSON dumps, and large PDF scans can dwarf the useful errors.
- A failed broad edit often causes the agent to retranslate unchanged sections. Rebuild using targeted `.tex` changes instead.
- Pseudocode, plot labels and original bibliography entries may be unnecessarily regenerated even when the source could be preserved safely.
- Many subagents can independently reread the same paper, increasing **total** tokens even if wall-clock time improves.

## Workflow with narrow context windows

**Initialize and inventory once.** Create a source PDF hash, source render images (stored locally), source blocks TSV, complete source headings/asset map, coverage ledger, and a glossary. Do not paste TSVs or entire rendered pages into the conversation. Keep the full inventory on disk. **Never accept the text extractor as the scientific source of truth.**

**Create per-section packets:**

```bash
make packets
# Inspect work/context-packets/index.md (small) and read ONE selected packet; the detailed JSON is for auditing.
# Later, avoid rereading approved blocks:
python3 scripts/prepare_section_packets.py --pending-only \
  --target sections/03-method.tex --out-dir work/pending-packets
```

`prepare_section_packets.py` uses the same heading and multi-column reading-order configuration as `seed_coverage.py`. It checks exact source-ID equality between the coverage ledger and the extracted source blocks. It never truncates a text block, even if doing so makes a packet larger than `--max-chars` (default: 12,000 **characters**, not tokens). It includes only glossary entries encountered in the packet. It does not call an LLM or change any coverage status. `index.json` lists all emitted source IDs and identifies sections needing mapping, while `index.md` is deliberately concise for the Agent.

**For each packet:**

1. Read the corresponding source page render(s) once. For plain prose, the extracted text is a navigation aid; for inline formulas, symbols, figure panels, tables or suspicious replacement characters, inspect original visuals at full resolution. Check column and page joins and section boundaries.
2. Translate the source into its local `sections/*.tex`, maintaining all scientific caveats, units, references, signs and symbol definitions. Reuse the project glossary. Never trim text to fit a context limit.
3. Compare translated text to source block IDs; manually confirm the reviewed subset in `work/coverage.tsv`, recording specific checks. If there are leftover `todo`s, keep them.
4. Run `make` for a concise build/QA summary. The *complete* TeX output is preserved at `work/latexmk-console.log`; inspect only relevant excerpts on failures. `make release` remains mandatory at final delivery.
5. Continue to the next packet; start a new session if needed, loading the small glossary, paper inventory, index, current section and unresolved issues. Do not load all prior chapter text unless cross-section consistency requires it.

**Resume state template** (a short file is sufficient, not a monolithic chat summary):

```text
Source: sources/original.pdf (record hash in work/inventory.md)
Reference backend: native or pdf
Approved glossary: work/glossary.tsv
Current target: sections/03-method.tex (packet 2/3)
Coverage: work/coverage.tsv (remaining todo IDs; refer to ledger)
Open issues: formula (7) source image p.6; cross-reference fig:3
Last successful: make (see build logs)
Next: finish packet 2, inspect p.6 formula, mark verified rows
```

## Tool-output budget

| Situation | Context to supply | Keep outside model context |
|---|---|---|
| Initial inventory | source page count, heading map, figure/formula counts, contact sheet | complete PDF object dumps and all PDF blocks |
| Section translation | relevant packet, compact glossary match, affected page images | unrelated chapters and hundreds of coverage rows |
| Vector crop check | current region preview(s), original crop boundary | all pages in full resolution |
| Compile success | exit status + diagnostic summary | latexmk package-loading transcript |
| Compile failure | targeted relevant `!`/file-line errors and related few log lines | complete log unless targeted investigation demands it |
| Hand-off to next agent | inventory, glossary, open issue list, next packet | full prior agent reasoning and complete chat history |

## Bibliography and math choices

For source-preserved English bibliographies, `BIB_MODE=pdf` avoids regenerating dozens of references; the link-restoration check remains strict. If the required output mandates semantically editable `.bib` and native citations, choose native mode and pay the necessary transcription/review cost. Never choose a cheaper format that violates user requirements. Retain original pseudocode and chart internals as native PDF objects; these are scientific assets, not translation targets by default.

Translating equations from original to semantic LaTeX requires careful recognition, and is not a good place for uncontrolled low-quality/model routing. Simpler prose drafting with a cheaper model *can* reduce API cost if the final high-quality review fully verifies each claim, but that is model/provider dependent and may increase corrections. This skill does not make API requests or select model tiers.

## Prompt caching (optional)

If your model provider has prefix caching, construct requests with an immutable prefix (role + condensed project policy + templates + stable glossary) and append changing packet material at the end. Test actual cache-hit statistics from your provider. Model-native tools and UI plans do not necessarily expose cache control. Keep output large enough to preserve all prose; do not use prompt compression that changes equations or drops qualifications.

## How to measure improvements

Compare the same paper and model in two executions, tracking **input tokens**, **cached input tokens**, **output tokens**, **reasoning tokens** if reported, *cost*, completeness failures, and agent rework attempts. Exclude initial package installation from LLM-token totals. File size in bytes or number of characters is not a reliable proxy for API token counts. No guaranteed percentage savings should be advertised without a controlled A/B test.

## Red lines

Do not: summarize instead of translate; skip references/appendices; trust only machine-extracted math; auto-approve coverage; suppress failed builds; blindly crop figures; omit final full-page visual QA; or declare a section correct merely because the packet exists.
