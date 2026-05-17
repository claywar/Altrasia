# packages/memory

WorldEngine **Memory** subsystem per [docs/02-memory.md](../../docs/02-memory.md).

## Responsibilities

- Loci (mind / world pools), diary capture + fan-out (MP-20)
- Mandatory recall assembly + cache (MEM-PERF-3, MEM-PERF-4)
- Recall protocol content
- Memory tool handlers (`memory_*`, `diary_*`)
- Blocking mode (MP-5, MP-9)

## Dependencies

- `packages/persistence` — all durable I/O via `PersistencePort`
- `packages/perception` — witnessed snippet eligibility
- `stripReasoning` from inference layer before writes (MP-14–MP-19)

## Out of scope

- [MemPalace/mempalace](https://github.com/mempalace/mempalace) (GitHub)
- Mem0, Zep, Letta as runtime backends
