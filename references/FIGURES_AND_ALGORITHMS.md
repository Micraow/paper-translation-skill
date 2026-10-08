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
      "label": "Algorithm 1, preserve verbatim",
      "kind": "algorithm"
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

### Numbering and clickable references (copyable recipes)

The generic `paper-translation.sty` already defines an **independent** `algorithm` float/counter. Do **not** wrap algorithms in `figure`: then "Algorithm 1" may become "图 15". Do **not** use `\caption*` followed by `\label`: a starred caption cannot create an incremented reference anchor.

**A. Complete crop includes the ORIGINAL "Algorithm 1" title:**

```tex
\numberedpreservedalgorithm[.94]{figures/algorithm01.pdf}{alg:sender}
正文：如算法~\ref{alg:sender} 所示，……
```

This steps the algorithm counter without duplicating the visible original heading. Check that the source's printed number equals the automatically stepped number. With gaps in the original numbering, set `\setcounter{algorithm}{<previous-original-number>}` before the block and verify the resulting clickable link.

**B. Crop is CODE/BODY ONLY (no printed title):**

```tex
\translatedalgorithm[.94]{figures/algorithm01-body.pdf}{发送端算法}{alg:sender}
正文：参见算法~\ref{alg:sender}。
```

Equivalent manual form:

```tex
\begin{algorithm}[htbp]
  \centering
  \includegraphics[width=.94\linewidth]{figures/algorithm01-body.pdf}
  \caption{发送端算法}\label{alg:sender}
\end{algorithm}
```

If the user supplied their own `.sty`, **do not change that shared template globally**: only if an algorithm environment does not already exist, declare `\newfloat{algorithm}{htbp}{loa}` and `\floatname{algorithm}{算法}` in the *local project preamble* (the `float` package is needed). Do not declare it twice or when another package already owns `algorithm`.


## Common crop defects

- legend clipped on the right;
- x-axis label clipped at bottom;
- line markers clipped at plot boundary;
- neighboring column text included;
- original caption partially included while a new caption is also typeset;
- insufficient whitespace causing the figure to look cramped in the translated layout.

Always inspect the final PDF render, not only the standalone crop preview.
