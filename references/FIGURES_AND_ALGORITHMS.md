# Figures, Tables, and Algorithms

## Why “extract the image” is often not enough

In scholarly PDFs, a visible figure may consist of:

- vector paths for axes and curves;
- text objects for tick labels and legends;
- one or more raster images;
- clipping masks and transparency layers.

`extract_image(xref)` only retrieves embedded raster objects. It may return just a background panel or one sub-image, not the complete figure.

Therefore inspect the page object structure first. If the figure is mixed/vector, crop the source PDF region into a new PDF page. This preserves the original objects and avoids rasterization.

## Vector crop workflow

1. Render the source page.
2. Generate a coordinate grid with `annotate_page_grid.py`.
3. Estimate a bounding box in PDF points `[x0, y0, x1, y1]`.
4. Add it to `assets/regions.json`.
5. Run `extract_vector_regions.py`.
6. Inspect the generated preview PNG.
7. Expand the box if any axis, legend, marker, line, annotation, or border is clipped.

PyMuPDF uses a top-left origin for page coordinates in these scripts, matching the visual grid output.

## Manifest example

```json
{
  "source": "../sources/original.pdf",
  "assets": [
    {
      "output": "fig1.pdf",
      "page": 3,
      "bbox": [318, 68, 552, 189],
      "label": "Figure 1 body only"
    },
    {
      "output": "algorithm1.pdf",
      "page": 9,
      "bbox": [52, 68, 296, 360],
      "label": "Algorithm 1, preserve verbatim"
    }
  ]
}
```

`page` is 1-based. Bounding-box coordinates are PDF points.

## Figure caption policy

Preferred:

- crop figure body only;
- translate caption in LaTeX;
- leave graph-internal scientific labels unchanged.

If the caption is tightly integrated into the figure and separating it risks clipping, keep the full original figure block and do not duplicate the caption.

## Tables

### Re-typeset when

- column labels need translation;
- the table is primarily text/numbers;
- a faithful LaTeX recreation is straightforward.

### Preserve visually when

- the table is unusually complex;
- exact typography/spacing is important;
- translating internal labels is not required;
- recreation risks introducing data errors.

In either mode, preserve every numeric value and footnote marker.

## Algorithms

Default: keep pseudocode/source code in the original language.

Best fidelity hierarchy:

1. vector PDF crop of the complete algorithm body;
2. direct text recreation only if the source is clean and exact;
3. raster image only when the original is raster.

Do not “improve” variable names, operation counts, line numbers, comments, arrows, or control-flow keywords.

## Common crop defects

- legend clipped on the right;
- x-axis label clipped at bottom;
- line markers clipped at plot boundary;
- neighboring column text included;
- original caption partially included while a new caption is also typeset;
- insufficient whitespace causing the figure to look cramped in the translated layout.

Always inspect the final PDF render, not only the standalone crop preview.
