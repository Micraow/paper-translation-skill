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
  \tag{8}\label{eq:rate}
\end{equation}
根据式~\eqref{eq:rate} ……
```

**Don't duplicate the source's equation number as literal prose** in place of a functioning semantic reference. Confirm `\tag` matches the source and a different equation does not accidentally reuse the same tag.

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
