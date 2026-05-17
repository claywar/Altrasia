# packages/persistence

SQLite persistence for WorldEngine v1 per [docs/11-data-model.md](../../docs/11-data-model.md).

## Responsibilities

- **`PersistencePort`** — sole interface for durable reads/writes (DM-8)
- **Migration 001** — core tables, composite indexes (DM-5), FTS5 virtual tables (DM-6)
- **`EmbeddingRecord`** table — created empty; populated by debounced embed jobs (INF-13)
- Scoped queries — no cross-`characterId` mind pool access (MP-1, DM-7)

## Migration 001 (normative)

1. Tables: `World`, `Scene`, `Character`, `Message`, `Locus`, `DiarySegment`, `EmbeddingRecord`, …
2. Indexes: see [11-data-model.md §4.1](../../docs/11-data-model.md)
3. FTS5: `Locus` and `DiarySegment` external-content indexes, synced on write
4. Unique: `(characterId, dedupeKey)` on `DiarySegment`

## Implementation notes

- Driver: `better-sqlite3` or `libsql` (DM-9)
- One DB file per operator (DM-1), e.g. `~/.worldengine/operator.db`
- Vector search v1: in-process cosine over `vectorBlob`; LanceDB sidecar only if benchmarks fail (11-data-model §4.4)

## Related

- [docs/02-memory.md](../../docs/02-memory.md) — memory subsystem
- [docs/17-acceptance-criteria.md](../../docs/17-acceptance-criteria.md) §7 — reference scale fixture
