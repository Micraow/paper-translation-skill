# Semantic cross-reference patterns (from precision-oriented LaTeX workflow)

## Figures and tables

```tex
\begin{figure}[htbp]
  \centering
  \includegraphics[width=.92\linewidth]{figures/fig01.pdf}
  \caption{中文图注，不篡改图中数据。}
  \label{fig:architecture}
\end{figure}
如图~\ref{fig:architecture} 所示，……
```

```tex
\begin{table}[htbp]
  \centering
  \caption{精确核对过的实验指标。}
  \label{tab:performance}
  \begin{tabular}{ll}
    \toprule 指标 & 数值 \\ \midrule
    Metric & 3.5 \\ \bottomrule
  \end{tabular}
\end{table}
参见表~\ref{tab:performance}。
```

## Equations and original numbering

```tex
\begin{equation}
  r(k+1)=r(k)+u(k).
  \label{eq:rate}  % prefer automatic equation numbering when it matches source
\end{equation}
根据式~\eqref{eq:rate} ……
```

**Prefer automatic numbering.** If the source calls this equation (8), make sure it really is (8) in the output; if not, adjust the starting counter for contiguous equations or use `\tag{8}\label{eq:rate}` as a *last resort* for irregular numbering. Explicit `\tag` can generate duplicate `xdvipdfmx: Object @equation.1 already defined` warnings with `hyperref` even when `\eqref` still works. Do not duplicate printed numeric text as a substitute for `\eqref`; audit the PDF named-destination tree and click representative links.

## Algorithms are not figures

The bundled template provides the `algorithm` float and a real counter/anchor. For original crops containing "Algorithm n", use `\numberedpreservedalgorithm{figures/alg.pdf}{alg:main}`. For cropped *body only*, use `\translatedalgorithm{figures/alg-body.pdf}{算法说明}{alg:main}`. Then `算法~\ref{alg:main}` is clickable. Never put `\label` after a `\caption*` and expect it to create a counter.

## Units and semantic emphasis

- `\qty{5.4}{\micro\second}` or `5.4\,\us` (the template's safe unit macro) rather than `\mathrm{\mu s}`; `unicode-math` may redirect `\mu` to U+1D707 in the text font.
- `\zhstrong{关键结论}` for visibly emphasized Chinese. The bundled source linter blocks `\emph{中文}` by default, and the log linter also blocks fallback italic/small-caps font substitutions. `\emph{中文}` often silently falls back to upright type because there is no CJK italic face.
- `\textsc{HPCC}` works in the bundled style with `lmromancaps10-regular.otf`; in third-party templates confirm a real small-caps face exists rather than trusting a font substitution warning.

## Chapters and appendices

```tex
\section{方法}\label{sec:method}
见第~\ref{sec:method}~节。
```

## Native reference list

```tex
根据已有工作~\cite{smith2020,wu2021} ……

\begin{thebibliography}{99}
\bibitem{smith2020} A. Smith. Original title. Venue, 2020.
\bibitem{wu2021} B. Wu. Original title. Venue, 2021.
\end{thebibliography}
```

These are **syntax examples only**, not actual source citations. Keep the paper's original bibliographic data when building real translated editions.

## Original reference PDF pages

This alternate mode does not use native `\cite` because the reference entries are imported PDF vector pages without TeX `\bibitem` anchors. Preserve original numeric `[n]` literals and run the strict GoTo annotation-restoration backend instead. The two modes must not be mixed.

## Audit

- `scripts/check_latex_project.py` discovers nested `\input` and `\include` recursively, checks key existence, duplicate labels, unresolved `\ref`s, and suspicious literal citations in native mode.
- Real compilation and log checking still required; complex macros and dynamic include paths cannot always be resolved statically.
- `scripts/audit_pdf.py` checks actual PDF internal link annotations (both GoTo and XeLaTeX named destinations).
- Open the output PDF and click a sampling of each link category before shipping.
