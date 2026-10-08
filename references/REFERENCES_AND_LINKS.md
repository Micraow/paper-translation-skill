# Two reference backends: native TeX vs original PDF pages

Never leave the source paper's in-text citations as dead text in the finished PDF.

## A. Native bibliography (`make`, default; preferred)

Choose when a complete bibliographic transcript or reliable `.bib` exists. Preserve original bibliography items, numbers and ordering, including identifiers and author names. Use `\cite{sourceKey}` and native `\bibitem{sourceKey}` or configured BibTeX/BibLaTeX; **do not manually type numeric citation brackets**. The generic sample uses `thebibliography` for portability.

For figures/equations/tables use `\label` and `\ref`/`\eqref`, even if original equation numbers need `\tag{...}`. The included `hyperref` makes links clickable. Static checks recursively scan chapter `.tex` files; compilation checks actual resolution; final PDF audit recognizes XeLaTeX `LINK_NAMED` anchors as legitimate internal destinations.

## B. Original bibliography pages (`make BIB_MODE=pdf`)

Choose when the references are more faithfully preserved as original PDF pages than as recreated entries. Set `\OriginalReferencePages` to the exact **source PDF** range, e.g. `14-17`, and keep source PDF at `sources/original.pdf`. Place visible `[1]`, `[9,32]` or `[3–5]` in translated prose exactly as in the source; do not mix in `\cite`.

Build:

```sh
make BIB_MODE=pdf
# Only if auto-detection is ambiguous (compiled final-PDF page numbers):
make BIB_MODE=pdf REF_START_PAGE=35 REF_END_PAGE=38
```

`Makefile` calls `scripts/add_reference_links.py --strict` unconditionally in this mode. It detects bibliography labels, wraps each visible citation number with an invisible internal PDF GoTo link, checks all printed numeral targets and fails for missing links/targets. Range expressions like `[3–5]` only expose the endpoints as separate clickable glyphs: if *every* intermediate number must have an independent link, print the full numeric list or choose native mode.

Script usage independently:

```sh
python scripts/add_reference_links.py build/main.pdf build/paper-final.pdf \
  --strict --report work/reference-links.json
python scripts/audit_pdf.py build/paper-final.pdf --mode pdf --strict
```

## Failures to check

- Original `References` header not present or other numeric `[n]` labels look similar → pass explicit final page range; inspect `work/reference-links.json`.
- Original PDF already contains correctly linked references → prefer retaining these links or native citations, and ensure the link-restoration pass does not duplicate them.
- PDFs processed by annotation-stripping tools sometimes share one `/Annots` array across pages. Our tool clones the shared arrays on affected pages to avoid cross-page duplicate annotations.
- Verify a citation from the beginning, middle and end of the paper by opening and clicking the final PDF. Static/link-count checks cannot prove all links are semantically correct.

A URL/DOI hyperlink (external website) is not equivalent to a local citation-to-bibliography GoTo.
