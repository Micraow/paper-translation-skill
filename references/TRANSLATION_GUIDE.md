# Translation Guide for Technical Papers

## Objective

Translate faithfully enough that a reader can reason from the Chinese version without needing the English text for ordinary comprehension, while still being able to map statements, equations, figures, and references back to the source.

## Fidelity rules

### Preserve epistemic strength

Do not turn:

- `may` into `will`;
- `can` into `must`;
- `suggests` into `proves`;
- `is associated with` into `causes`;
- `up to 47.6%` into `47.6%` without the qualifier.

### Preserve comparison direction

For phrases such as:

- `X is 3.5x faster than Y`;
- `X reduces latency by 41% compared with Y`;
- `X is 15% lower than Y`;

keep the baseline and direction explicit in Chinese.

### Preserve scope

Technical papers often qualify a claim with a scenario, topology, workload, percentile, or region. Keep those qualifiers adjacent to the claim.

Bad:

> CCC 的时延更低。

Better:

> 在场景 S1 中，CCC 的 99.9% 尾时延更低。

## Terminology

At first substantive use:

```text
拥塞信息推断（congestion information deduction，CiD）
```

Then use `CiD` or the established Chinese term consistently.

Do not repeatedly expand abbreviations in every section unless the source does so for clarity.

### Names that normally stay untranslated

Keep system/protocol/framework names as identifiers:

- DCTCP
- DCQCN
- TIMELY
- SWIFT
- HPCC
- PowerTCP
- DPDK
- PFC
- ECN
- INT
- RTT
- BDP

Translate the surrounding concept, not the identifier.

## Mathematical prose

Variables remain variables. Do not translate them into prose names inside formulas.

Example:

```text
where R(k) is the aggregated arrival rate
```

becomes:

```text
其中，R(k) 表示聚合到达速率。
```

Do not rename `R(k)` to a Chinese symbol.

## Figure references

Keep source numbering:

- `Fig. 4` -> `图 4`
- `Table 1` -> `表 1`
- `Eq. (7)` -> `式 (7)` or `公式 (7)`
- `§4.3.2` -> `§4.3.2` or `第 4.3.2 节`

Choose one style and stay consistent.

## Algorithm pseudocode

Default: **do not translate**.

Reasons:

- identifiers and comments may be semantically coupled to implementation;
- translated pseudocode makes source comparison harder;
- preserving the original vector algorithm block avoids reflow mistakes.

Translate only the prose that introduces/explains the algorithm, and optionally a separable caption if requested.

## Bibliography

Do not translate paper titles/authors/venue names in the references. Keep source spelling and numbering.

## Prohibited shortcuts

Do not:

- summarize a paragraph instead of translating it;
- omit parenthetical caveats because they feel repetitive;
- rewrite multiple sentences into one if any logical relation becomes ambiguous;
- infer missing content from domain knowledge without marking it as external;
- silently fix an apparent paper error. Preserve it and, if necessary, add an explicit translator note.

## Preferred Chinese prose style

Aim for natural technical Chinese rather than word-for-word English syntax:

- keep subject/object relations explicit;
- avoid excessive passive constructions when Chinese can state the actor clearly;
- split extremely long English sentences if needed, but preserve every clause and logical relation;
- keep numerical results close to the metric and baseline they describe;
- use Chinese punctuation in prose and standard mathematical punctuation in formulas.

## Final consistency pass

Before delivery, search the project for:

- inconsistent translations of repeated technical terms;
- inconsistent full-width/half-width punctuation around abbreviations;
- mismatched figure/table/equation numbers;
- stray English prose that should have been translated;
- accidentally translated pseudocode or bibliography entries.

## Fidelity hierarchy (adopted as a hard editorial rule)

When priorities conflict: **mathematical meaning > logical force/scope > stable terminology > faithful structure > Chinese fluency > stylistic elegance.** Do not make an unsupported scientific claim stronger merely to smooth a Chinese sentence.

| English cue | Chinese translation constraint |
|---|---|
| may, might | 可能；不得加强成“必然” |
| can | 可以、能够；根据上下文区分能力与许可 |
| should | 应、应当；不要无条件译为“必须” |
| must | 必须；保持必要性 |
| likely | 很可能、可能性较大；保持不确定性 |
| we observe/find | 我们观察到／发现；不要升级成普遍定理 |
| we show | 我们表明；只有原文确实给出证明才说“证明” |
| suggest | 提示、表明或暗示；按上下文保留强度 |

When authors make factual mistakes, do not silently rewrite their results with outside knowledge. A clearly separated, short translator's note may be used only if the reader genuinely needs it. Preserve all measurement values (especially `µs`, `ms`, `Gbps`, `GB/s`, percentile directions, ratio denominators and figures' axis legends).
