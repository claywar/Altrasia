# Output quality fixtures

Acceptance fixtures for v1 blocking tests OQ-1 and OQ-3 ([17-acceptance-criteria.md](../../../docs/17-acceptance-criteria.md) §2b, §10).

## Contents (implementation)

| Artifact | Purpose |
|----------|---------|
| `prompt-addendum-snapshot.json` | Mock LLM: assembled generation request includes quality addendum when profile enables OQ-1 |
| `short-roleplay-script.json` | Nightly e2e: 3-turn exchange; manual/automated check for obvious repetition loops |

Profile: `qwen3.6-35b-a3b`
