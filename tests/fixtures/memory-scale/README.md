# Memory scale fixture

Synthetic dataset for MEM-PERF-2/3/4 and MEM-ACC-1 ([docs/17-acceptance-criteria.md](../../../docs/17-acceptance-criteria.md) §7).

## Target dimensions

| Dimension | Size |
|-----------|------|
| Characters | 24 |
| Diary segments (total) | 12,000 |
| Mind loci per character | ~200 keys, ~2MB aggregate text |
| World loci per scene | ~100 keys |

## Artifacts (implementation)

| Artifact | Purpose |
|----------|---------|
| [generator-spec.json](generator-spec.json) | Parameters for `scripts/seed-memory-scale.ts` |
| `memory-scale.sqlite` | Optional checked-in snapshot (git-lfs if large) |

## Generator spec

Run generator when persistence exists:

```bash
# illustrative
npx ts-node scripts/seed-memory-scale.ts --out tests/fixtures/memory-scale/memory-scale.sqlite
```

## Tests

- **MEM-ACC-1:** 10k randomized hybrid searches — zero cross-character mind-pool hits
- **MEM-PERF-2:** p95 `memory_search` / `diary_search` <50ms on reference hardware
- **MEM-PERF-3:** p95 mandatory recall assembly (cache miss) <100ms
- **MEM-PERF-4:** SQL scoped to single `characterId` + active `sceneId`

Reference hardware profile: TBD ([docs/ROADMAP.md](../../../docs/ROADMAP.md)).
