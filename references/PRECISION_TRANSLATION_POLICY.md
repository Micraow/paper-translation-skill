# Translation Policy for Academic Papers

## 1. Fidelity hierarchy

When choices conflict, use this priority:

1. mathematical/technical meaning;
2. scope and logical force;
3. terminology consistency;
4. structure and traceability;
5. Chinese fluency;
6. stylistic elegance.

A polished sentence that changes claim strength is worse than a slightly less elegant faithful sentence.

## 2. Modal and epistemic language

Preserve distinctions:

| Source | Typical Chinese force |
|---|---|
| may | 可能 / 可以（按语境） |
| can | 可以 / 能够 |
| should | 应 / 应当 / 理应 |
| must | 必须 |
| likely | 很可能 / 可能性较高 |
| we observe | 我们观察到 |
| we find | 我们发现 |
| we show | 我们表明 / 我们证明（只有确实是证明时） |
| suggest | 表明 / 暗示（按语境，不自动强化） |

## 3. Terms and acronyms

At first occurrence, use a compact bilingual definition when it aids the reader:

```text
远程直接内存访问（Remote Direct Memory Access，RDMA）
显式拥塞通知（Explicit Congestion Notification，ECN）
```

Thereafter prefer the acronym or stable Chinese term. Do not redefine the acronym repeatedly.

Keep proper names (DCTCP, TIMELY, RoCEv2, InfiniBand, Mellanox, Arista) stable.

## 4. Numbers and units

Never “normalize” a paper's measured value without source evidence.

Preserve:

- `40Gbps` vs `40 Gbps` according to the chosen document convention, but not `40GB/s`;
- `µs` vs `ms`;
- percentile direction (`10th percentile` is not `90th percentile` unless the paper explicitly maps throughput to response time);
- ratios such as `16:1`;
- source-defined thresholds and constants.

For XeLaTeX with `unicode-math`, treat units as units, **not italic mathematical identifiers**: `\qty{5.4}{\micro\second}` or `\SI{5.4}{\micro\second}` is safe with the bundled `siunitx`; `5.4\,\us` uses the style's microseconds macro. Do **not** use `$5.4\mathrm{\mu s}$`: it can request U+1D707 from Latin Modern Roman (a missing glyph). Apply the same semantic care to `\ohm`, degrees, micro-metres, and similar prefixes: keep their mathematical meaning and unit symbols exact.

## 5. Mathematical prose

Variables should stay as variables:

Bad: “当前速率乘以阿尔法的一半” when the source references `R_C α / 2` and the equation is nearby.

Better: keep `$R_C$`, `$\alpha$`, `$K_{\min}$` in prose.

## 6. Citations

Do not translate a citation marker as text. Attach `\cite{key}` to the corresponding statement.

Keep bibliography titles/authors/venues in their source bibliographic form unless the user explicitly requests translated reference titles.

## 7. Source errors and oddities

If the source contains a typo or odd numbering:

- preserve it when silently changing it would make the translation no longer traceable;
- if necessary, add a short translator note clearly marked as such;
- do not silently “repair” experimental values or formulae using external knowledge.

## 8. What not to add

Unless requested, do not add:

- tutorials;
- modern comparisons;
- “in other words” paragraphs not present in the source;
- external citations;
- critique;
- claims about later deployment status.

Those can be provided in a separate commentary after the faithful translation.
