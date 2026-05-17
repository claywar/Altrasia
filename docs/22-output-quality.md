# 22 — Output Quality

Cross-cutting policy for **model output shape**: convergence, anti-repetition, and reasoning hygiene. This complements memory discipline ([16-learning.md](16-learning.md)) and prompt layers ([10-prompt-injection.md](10-prompt-injection.md)).

## 1. Goal

The model SHOULD **finish** a coherent in-character reply instead of thinking in circles or repeating the same phrase until max tokens.

**Deep reasoning is allowed**; the target is **convergence** and **non-repetitive surface text** in `outputText`, not reduced reasoning budget.

## 2. Principles

| ID | Principle |
|----|-----------|
| OQ-1 | Output-quality policy travels with every generation profile—not tied to one preset or UI mode. |
| OQ-2 | Mitigations use prompt discipline, context hygiene, sampling, and length/stop shape—not throttling reasoning effort by default. |
| OQ-3 | Reasoning MUST NOT leak into durable memory or the next turn's visible transcript ([16-learning.md](16-learning.md) MP-14–MP-19). |
| OQ-4 | Anti-loop inject MUST NOT contradict mandatory recall or scene framing authority. |

## 3. Policy layers

Implementations SHOULD apply quality policy through one or more of:

| Layer | Purpose |
|-------|---------|
| **System / developer addendum** | Finish the reply; do not restate the same sentence; stop when the beat is complete |
| **Model profile** | `stripReasoningTags`, stop sequences, max output tokens ([00-inference-runtime.md](00-inference-runtime.md)) |
| **Sampling** | Modest frequency penalty / repetition penalty where the backend supports it |
| **Prompt audit** | Remove chain-of-thought templates that encourage endless branching in the same job |

Policy MUST be configurable per `modelProfile` and overridable per world preset.

## 4. Reasoning handoff

When the API returns separate reasoning fields:

1. Strip before persisting transcript, diary, and loci (`stripReasoning`).
2. Do not echo prior reasoning blocks into the next user/assistant turn unless operator enables debug-only display ([14-web-ui.md](14-web-ui.md) UI-W5).

## 5. Verification

| Check | Method |
|-------|--------|
| No duplicate spans in final reply | Fixture conversations; manual golden-path spot checks |
| Reasoning absent from diary/loci | MP-14–MP-18 acceptance fixtures |
| Policy present in assembled prompt | Integration test: generation request includes profile quality addendum when enabled (v1 **blocking** — [17-acceptance-criteria.md](17-acceptance-criteria.md) §2b) |

## 6. Requirements summary

| ID | Requirement |
|----|-------------|
| OQ-1 | Quality addendum configurable per model profile; applies to cast and Observer generations unless disabled. |
| OQ-2 | Sampling knobs documented in model profile YAML; safe defaults for roleplay preset. |
| OQ-3 | stripReasoning runs before durable writes and before diary fan-out snippet assembly. |
| OQ-4 | Quality inject uses distinct marker; stripped on regenerate like mandatory recall (PI-1 pattern). |

**v1 release:** OQ-1 and OQ-3 are blocking CI gates ([17-acceptance-criteria.md](17-acceptance-criteria.md) §2b). Fixtures: `tests/fixtures/output-quality/`.

## Related documents

- [00-inference-runtime.md](00-inference-runtime.md)
- [10-prompt-injection.md](10-prompt-injection.md)
- [16-learning.md](16-learning.md)
- [17-acceptance-criteria.md](17-acceptance-criteria.md)
