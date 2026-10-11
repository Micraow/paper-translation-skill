# Translation policy

Rules only. The *workflow* lives in `SKILL.md`; the compilation traps live in
`PITFALLS.md`. This file used to be two documents (`TRANSLATION_GUIDE.md` +
`PRECISION_TRANSLATION_POLICY.md`) that repeated seven topics with slightly different
wording — merged here so each rule is stated once.

## Fidelity hierarchy (hard editorial rule)

When priorities conflict:

**mathematical/technical meaning > scope & logical force > terminology consistency >
structure & traceability > Chinese fluency > stylistic elegance.**

A polished sentence that changes claim strength is worse than a plainer faithful one.

## Modal and epistemic language

Never strengthen or weaken the author's commitment:

| Source cue | Chinese | Constraint |
|---|---|---|
| may, might | 可能 | 不得加强成“必然” |
| can | 可以、能够 | 按语境区分能力与许可 |
| should | 应、应当 | 不要无条件译为“必须” |
| must | 必须 | 保持必要性 |
| likely | 很可能 | 保持不确定性 |
| we observe / we find | 我们观察到／发现 | 不要升级成普遍定理 |
| we show | 我们表明 | 只有原文确实给出证明才说“证明” |
| suggest | 提示、表明或暗示 | 按上下文保留强度 |

Preserve causal direction (`is associated with` ≠ `causes`, `suggests` ≠ `proves`) and
comparison baselines: `X is 3.5× faster than Y`, `X reduces latency by 41% compared
with Y`, `X is 15% lower than Y` must keep both baseline and direction in Chinese.
Keep any scenario, topology, workload, percentile or region qualifier adjacent to the
claim it limits — “在场景 S1 中，CCC 的 99.9% 尾时延更低”, not “CCC 的时延更低”.

## Terminology

Define a term bilingually at first substantive use, then stay consistent:

```text
拥塞信息推断（congestion information deduction，CiD）
远程直接内存访问（Remote Direct Memory Access，RDMA）
```

Do not re-expand an abbreviation in every section unless the source does. Record
project decisions in `work/glossary.tsv`.

Keep identifiers as identifiers — system/protocol/framework names such as DCTCP,
DCQCN, TIMELY, SWIFT, HPCC, PowerTCP, DPDK, PFC, ECN, INT, RTT, BDP, RoCEv2,
InfiniBand, Mellanox, Arista — and translate the surrounding concept, not the name.

## Numbers and units

Never “normalize” a measured value without source evidence. Preserve `40Gbps` vs
`40 Gbps` according to the chosen document convention but never `40GB/s`; µs vs ms;
percentile direction (`10th percentile` is not `90th percentile` unless the paper
explicitly maps throughput to response time); ratios such as `16:1`; and
source-defined thresholds, constants, error bars and graph-axis scales.

Treat units as units, not as italic mathematical identifiers. With `unicode-math`,
`\qty{5.4}{\micro\second}` / `\SI{5.4}{\micro\second}` / the style's `5.4\,\us` are
safe; `$5.4\mathrm{\mu s}$` can request a missing glyph. Apply the same care to
`\ohm`, degrees and micro-metres. See `PITFALLS.md` for the glyph trap.

## Mathematical prose

Variables stay variables. “当前速率乘以阿尔法的一半” is wrong when the source has
`$R_C\,\alpha/2$`; keep `$R_C$`, `$\alpha$`, `$K_{\min}$` as math inside prose.

## Citations

Never translate a citation marker into text. In `native` mode attach `\cite{key}` to
the statement; in `pdf` mode preserve the visible `[n]` exactly as printed. Keep
bibliography titles, authors and venues in their source bibliographic form unless the
user explicitly asks for translated reference titles.

## Source errors and oddities

Do not infer missing content from domain knowledge without marking it as external. Do
not silently fix an apparent paper error: preserve it, keep numbering traceable, and if
the reader genuinely needs it add a short translator's note clearly marked as such.
Never “repair” experimental values or formulae using outside knowledge.

## Prohibited shortcuts

Do not: summarize a paragraph instead of translating it; omit parenthetical caveats
because they feel repetitive; merge several sentences into one if any logical relation
becomes ambiguous; translate pseudocode or bibliography entries; insert your own
analysis, critique or external citations into the translated body.

## Preferred Chinese prose style

Natural technical Chinese rather than word-for-word English syntax: keep subject/object
relations explicit; avoid excessive passive when Chinese can state the actor; split
extremely long sentences only if every clause and logical relation survives; keep
numerical results close to the metric and baseline they describe; use Chinese
punctuation in prose and standard punctuation in formulas.

## Final consistency pass

Before delivery, search the project for: inconsistent translations of repeated
technical terms; full-width/half-width punctuation around abbreviations; mismatched
figure/table/equation numbers; stray English prose that should have been translated;
accidentally translated pseudocode or bibliography entries.

## What not to add (unless requested)

Tutorials; modern comparisons; “in other words” paragraphs absent from the source;
external citations; critique; claims about later deployment status. If such material is
wanted, put it in a clearly separated commentary after the faithful translation.
