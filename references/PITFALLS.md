# Compilation and typesetting pitfalls

“How it bites, and how to get out.” The *rules* live in `SKILL.md` and
`references/TRANSLATION.md`; this file collects the traps so a rule and its failure
mode are not split across files. Mostly relevant to Phases 3–6.

## Algorithms need their own counter — not `figure`, not `\caption*`

A vector crop of “Algorithm 1” wrapped in a plain `figure` with `\caption*` cannot be
`\ref`-ed (`\label` needs a stepping counter) and would be numbered as a figure. The
bundled style already provides the `algorithm` float plus
`\numberedpreservedalgorithm` (crop keeps the original heading) and
`\translatedalgorithm` (code-only crop). For a user-owned template, declare a local
float in the project preamble instead of editing their global `.sty`:
`\newfloat{algorithm}{htbp}{loa}` + `\floatname{algorithm}{算法}` (needs `float`); do
not declare it twice if another package already owns `algorithm`. Note the override in
the delivery notes.

## Prefer automatic equation numbering over `\tag`; audit the name tree

`\tag{n}` pins a number, but under `hyperref` + `amsmath` it can emit a second
destination (`equation.1`) alongside the `AMS.n` destination used by `\eqref`,
producing `xdvipdfmx: warning: Object @equation.n already defined`. If numbered
equations already run 1..N in source order, drop `\tag` and keep only `\label`; for a
contiguous offset use `\setcounter{equation}{<previous>}`. Reserve `\tag` for irregular
numbering. Then audit the compiled `/Names` tree, not merely the link list:

```python
import pymupdf
with pymupdf.open('build/paper-final.pdf') as pdf:
    for name, data in pdf.resolve_names().items():
        print(name, data)
```

Each key must appear exactly once. A clean name tree still does not prove the targets
are right — click representative equation and citation links.

## Units: keep the micro sign upright

With `unicode-math`, `\mathrm{\mu}` does **not** yield U+00B5 — it requests U+1D707,
which the Latin text font lacks, and `check_latex_log.py` then fails on
`missing_character`. Write `\si{\micro\second}` / `\SI{5.4}{\micro\second}`, or the
style's `\us`, both of which render U+00B5 upright. Check any Greek symbol that is
really a *unit* the same way (never change the scientific quantity itself).

## Never reproduce the source's literal `[n]` in native mode

The linter's hard-coded-citation regex also fires on a bracketed number inside a
translator note. Write “同一篇参考文献（编号 8）” rather than `参考文献~[8]`.

## CJK emphasis and small caps can silently substitute

Many CJK fonts have no italic face, so `\emph{中文}` quietly renders upright and the
emphasis is lost; Latin `\textsc` can silently fall back too. The default gates
**reject** literal CJK `\emph` and reject italic/small-caps font-shape substitution in
the log. Use `\zhstrong{...}` / `\textbf{...}`, and confirm a real small-caps face
(bundled Latin Modern Caps) instead of dismissing the warning as cosmetic.

## `Missing character` is never cosmetic

Every `Missing character` line fails the log gate. Fix the source glyph or the macro;
never disable the check to hide it.

## Environment warnings that are not translation defects

`pdftex.map` / `kanjix.map` warnings from `xdvipdfmx` usually mean an incomplete
optional TeX font-map configuration. If output fonts and glyphs are correct, treat it
as an environment warning — and do **not** loosen the real glyph/QA gates to silence
unrelated noise.
