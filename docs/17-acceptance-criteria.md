# 17 — Acceptance Criteria

Test matrix mapping requirement IDs to verifiable scenarios. v1 release gate: **spatial golden path** + inference spike tests.

## 1. Test layers

| Layer | Runs in CI | Runs nightly |
|-------|-----------|--------------|
| Unit | Yes | Yes |
| Integration | Yes (mock LLM) | Yes |
| Golden path e2e | No | Yes (real llama.cpp, Qwen3.6-35B-A3B) |

Reference model profile: `qwen3.6-35b-a3b` / router id `Qwen3.6-35B-A3B`.

## 2. Spatial golden path (v1 release)

| Step | Verifies |
|------|----------|
| 1 | Create world with ≥2 scenes, exits, 2 NPCs, persona in scene A |
| 2 | Public line → NPC reply; whisper does not leak in other cast prompts |
| 3 | Move persona to scene B; elsewhere roster shows NPC + scene label |
| 4 | Knock signal on exit; target scene banner; persists after restart (CC-2) |
| 5 | Observer meta-chat renames scene / fixture; framing updates (OBS-2, UI-OBS-CHAT) |
| 6 | Restart server; presence, exits, signals hydrate (MP-11, CC-2) |
| 7 | Group scene: Alice and Bob present; Alice public line → Bob replies; restart → Bob mandatory recall diary contains Alice's line (MP-6, MP-17, MP-20) |

## 3. Requirement matrix

### World and presence

| ID | Test |
|----|------|
| W-1 | Delete last scene rejected |
| W-3 | Character cannot be present in two scenes |
| LP-1 | Join removes from other scene present list |
| CC-1 | exitsJson round-trip |
| CC-3 | Elsewhere roster includes presentSceneId |

### Memory

| ID | Test |
|----|------|
| MP-1 | Mind search for Alice never returns Bob mind loci |
| MP-8 | Observer generation includes mandatory recall block |
| MP-9 | First model call with blocking on has only memory_* tools |
| MP-11 | After restart, recall contains loci not lost transcript-only facts |
| MP-6 | Diary segment text includes witnessed persona/cast lines in rolling window, not speaker-only |
| MP-17 | Diary snippet uses stripped outputText per line; think blocks absent |
| MP-20 | After Alice speaks and Bob replies in group scene, both diaries contain same dedupeKey segment |
| MP-20b | After restart, Bob mandatory recall includes Alice's public line from diary without full transcript |
| MP-14–MP-18 | stripReasoning fixtures: think tags not in diary/loci |
| MP-16 | memory_store with reasoning-only rejected |
| MEM-ACC-1 | 10k randomized hybrid searches: zero Bob mind-pool hits when querying as Alice |
| MEM-ACC-2 | Mandatory recall diary tail ordering matches newest `createdAt` within budget |
| MEM-ACC-5 | Assembled mandatory recall char length ≤ `mandatoryRecallMaxChars` |

### Memory performance (v1 gate)

| ID | Test |
|----|------|
| MEM-PERF-1 | Tool search uses FTS path (no full scan — assert via query plan or mock counter) |
| MEM-PERF-2 | On reference scale fixture: p95 `memory_search` / `diary_search` &lt;50ms |
| MEM-PERF-3 | On reference scale fixture: p95 mandatory recall assembly (cache miss) &lt;100ms |
| MEM-PERF-4 | Recall assembly SQL/API calls scoped to single `characterId` + active `sceneId` only |

### Observer and roles

| ID | Test |
|----|------|
| ROLE-1 | Cast prompt assembly excludes observer digest |
| OBS-5 | World fixture change without tool not persisted |
| OBS-4 | narrator scope visible to present cast only |

### Inference and queue

| ID | Test |
|----|------|
| INF-5 | Two simultaneous unqueued GPU calls impossible |
| INF-5a | Tool recurse holds same lease |
| INF-5d | At maxDepth, idle job not enqueued |
| INF-2 | Change modelProfile without server restart |
| STR-1–STR-4 | Stream events received; final DB row post-strip |
| — | Router model id matches `Qwen3.6-35B-A3B` |

### Orchestration

| ID | Test |
|----|------|
| AO-11 | Second job waits until lease released |
| AO-12 | Idle tick skipped when queue full |

### Communication (v1)

| ID | Test |
|----|------|
| — | canPerceive table: public, whisper, DM, narrator |
| CC-5 | Message with phone metadata parses; UI does not send phone in v1 |
| — | Meta messages excluded from cast prompt assembly |

### Meta channel

| ID | Test |
|----|------|
| — | POST meta-message not returned in scene transcript GET |
| — | Cast canPerceive false for channelKind=meta |

## 4. v1.1 gate (addendum)

| ID | Test |
|----|------|
| C-9 / CC-8 | Kitchen bystander hears Alice phone lines only, not Bob leg (handset) |
| C-10 / CC-9 | Speakerphone on kitchen only: kitchen bystanders hear both sides; hall bystanders still one side |
| C-11 | Speakerphone on both ends independently toggled |
| C-5 / CC-10 | Mirror stub on remote transcript; perception rules apply |
| CC-11 | Knock answer triggers generation or join |

## 5. Output quality (non-blocking v1)

| ID | Test |
|----|------|
| OQ-1 | Roleplay model profile includes quality addendum when enabled |
| OQ-3 | Reasoning blocks absent from next-turn visible transcript after strip |

## 6. Future (non-blocking v1)

| ID | Test |
|----|------|
| MAP-7 | Map regen fixture diff surfaces conflict |
| IMG-1, IMG-8 | ComfyUI via queue; yields to Observer Direct |

## 7. Reference scale fixture (memory performance)

CI MUST include a synthetic dataset at approximately:

| Dimension | Size |
|-----------|------|
| Characters | 24 |
| Diary segments (total) | 12,000 |
| Mind loci per character | ~200 keys, ~2MB aggregate text |
| World loci per scene | ~100 keys |

Path: `tests/fixtures/memory-scale/` (seed script + SQLite snapshot or generator).

Performance tests (MEM-PERF-2, MEM-PERF-3) run against this fixture on every CI integration job. Leakage tests (MEM-ACC-1) run 10k randomized queries.

## 8. stripReasoning fixtures

Maintain `tests/fixtures/strip-reasoning/` with:

- Raw Qwen output samples (with think blocks)
- Expected `outputText`
- Profile `qwen3.6-35b-a3b`

## Related documents

- [02-memory.md](02-memory.md)
- [11-data-model.md](11-data-model.md)
- [20-product-principles.md](20-product-principles.md)
- [00-inference-runtime.md](00-inference-runtime.md)
- [16-learning.md](16-learning.md)
