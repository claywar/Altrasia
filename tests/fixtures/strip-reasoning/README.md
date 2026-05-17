# stripReasoning fixtures

Samples for MP-14–MP-18 and OQ-3 ([docs/17-acceptance-criteria.md](../../../docs/17-acceptance-criteria.md) §9, [docs/16-learning.md](../../../docs/16-learning.md)).

Profile: `qwen3.6-35b-a3b` — tag pairs in [`config/models/qwen3.6-35b-a3b.yaml`](../../../config/models/qwen3.6-35b-a3b.yaml).

## Files

| File | Purpose |
|------|---------|
| [qwen-think-tags.json](qwen-think-tags.json) | `redacted_thinking` wrapper stripped from durable text |
| [qwen-api-reasoning-field.json](qwen-api-reasoning-field.json) | Separate `reasoning_content` field stripped before persist |

## Test contract

Each fixture:

```json
{
  "profileId": "qwen3.6-35b-a3b",
  "rawModelOutput": { },
  "expectedOutputText": "string without reasoning",
  "mustNotContain": ["<think>", "reasoning_content"]
}
```

Implementations MUST assert `expectedOutputText` equals `stripReasoning(rawModelOutput)` and that diary/locus writes use only `outputText`.
