# Delivery QA Checklist

Use this as a hard gate before returning a translated paper.

## Semantic completeness

- [ ] All source sections/subsections are present in order.
- [ ] Coverage ledger has no meaningful `todo` rows.
- [ ] Page/column boundary sentences were explicitly checked.
- [ ] All footnotes are represented.
- [ ] All numbered equations are represented and correctly numbered.
- [ ] All figure/table/algorithm references point to the correct number.
- [ ] No results, qualifiers, ranges, percentiles, or baselines were dropped.
- [ ] Terminology is consistent across the document.
- [ ] No external knowledge was silently inserted into the translation.

## Preservation rules

- [ ] Algorithm pseudocode/code remains source-language unless explicitly requested otherwise.
- [ ] Bibliography entries remain original-language and in original order.
- [ ] Figure data is unchanged.
- [ ] Figure-internal labels remain original unless explicitly redrawn/translated.
- [ ] Formula symbols and variable names are unchanged.

## Visual assets

- [ ] Each figure was classified as raster vs vector/mixed before extraction.
- [ ] Vector/mixed figures use PDF crops rather than screenshots.
- [ ] No axis, legend, label, marker, or border is clipped.
- [ ] Crops do not accidentally include neighboring prose.
- [ ] Tables contain exact numeric values.

## LaTeX/build

- [ ] XeLaTeX build succeeds from clean state.
- [ ] No unresolved references/citations.
- [ ] No missing-character warnings.
- [ ] No serious overfull boxes.
- [ ] No proprietary font files are packaged.

## PDF behavior

- [ ] Final PDF opens normally.
- [ ] Internal citation links exist.
- [ ] Sample citation links land on correct references.
- [ ] URLs/DOIs remain clickable where appropriate.
- [ ] Page numbering is sensible.

## Render inspection

- [ ] Contact sheet inspected.
- [ ] Cover/title page inspected full-size.
- [ ] Every figure/table page inspected full-size.
- [ ] Every algorithm page inspected full-size.
- [ ] Long-equation pages inspected full-size.
- [ ] First/last reference pages inspected full-size.
- [ ] Appendix pages inspected.
- [ ] No clipping, overlap, black boxes, broken glyphs, or accidental blank pages.

## Deliverable package

- [ ] Final PDF included.
- [ ] Source archive included.
- [ ] Crop manifest included.
- [ ] Extracted vector assets included.
- [ ] Rebuild scripts included.
- [ ] Build instructions included.
- [ ] No unrelated personal data included.
