# 02 — Memory

Altrasia **Memory** is the structured memory subsystem: **loci** (semantic facts), **pools** with strict privacy, an episodic **diary**, and prompt-time **recall** so characters answer consistently without leaking private knowledge.

> **Not MemPalace (GitHub).** This subsystem is Altrasia Memory. It does **not** embed, depend on, or implement the [MemPalace/mempalace](https://github.com/mempalace/mempalace) open-source project (Wings/Rooms/Closets/Drawers, ChromaDB, coding-session mining). Requirement IDs use the **`MP-*`** prefix (memory requirement).

## 1. Concepts

### 1.1 Locus

A **locus** is a stable string key naming a memory slot. Each locus holds a **string value** (free text). Storing to an existing locus MUST **append** new text (e.g. separated by newline), not replace silently, unless an explicit overwrite API is added for operators.

```
locus "kitchen_layout" → "North wall: hearth. East: pantry door."
```

### 1.2 Pools

Facts live in one of two **pools**:

| Pool | Scope | Visibility |
|------|-------|------------|
| **Mind** | Per `characterId` (global across worlds/scenes) | Only that character's tools and recall |
| **World** | Per `sceneId` (or active scene in a world) | All agents with access to that scene's world pool |

**Privacy invariant (MP-1):** Mind pool data MUST NEVER appear in another character's tool results, prompt recall blocks, or search hits. Cross-character knowledge MAY only enter through the **transcript** (dialogue, actions visible in chat).

**World pool semantics:** Objective facts everyone present could observe—room layout, props, shared events. Not private thoughts.

Pool aliases for tools (SHOULD accept): `mind` ← `character`, `self`; `world` ← `global`, `scene`.

### 1.2.1 World commons (optional, post-v1)

**World commons** are institutional records in the **world aggregate** ([01-world-model.md](01-world-model.md)), keyed `world:{worldId}:commons:{key}`. They are not mind pool (MP-1) and not scene-local world pool.

| Rule | Level |
|------|-------|
| Commons appear in mandatory recall only for `characterId` on `commonsAccessIds` for that world | MUST (MP-22) |
| Commons MUST NOT bypass MP-1 for characters not on the allowlist | MUST |
| Prompt inject labels commons as records available to the character, not facts everyone already knows | SHOULD (ROLE-6) |

See [23-in-world-work.md](23-in-world-work.md) §5.

### 1.2.2 Commission and debate loci (post-v1)

Research **commissions** default to **mind pool** storage (COM-1, COM-2 in [23-in-world-work.md](23-in-world-work.md)). Recommended key prefixes:

| Prefix | Pool | Owner |
|--------|------|-------|
| `commission:{commissionId}:` | mind | assignee `characterId` |
| `debate:{sceneId}:` | mind | each debate participant |

**Idle social (implemented):**

| Prefix | Pool | Owner |
|--------|------|-------|
| `relationship:{characterId}` | mind | each NPC (notes about counterpart) |
| `culture:norms`, `culture:recent` | world | scene (`ownerId` = `sceneId`) |

Cast MAY write these via tool `social_signal` during `banter_turn` / `idle_continue` when `socialSignalEnabled` is true.

### 1.3 Diary (witnessed episodic memory)

The **diary** is **witnessed episodic memory**: what a character could have heard or seen in play, captured automatically after each completed cast reply. It is **not** a log of that character's own monologue alone.

Each **diary segment** SHOULD include:

| Field | Purpose |
|-------|---------|
| `text` | Formatted excerpt (witnessed dialogue window) |
| `createdAt` | ISO timestamp |
| `sourceSceneId` | Where it was captured |
| `messageIds` | Provenance |
| `dedupeKey` | Prevent duplicate capture |
| `kind` | Optional category |

Diary is **per character** (global), not per scene. Segments MAY reference which scene they came from. In group scenes, multiple characters MAY hold segments with the **same** `text` and `dedupeKey` (fan-out; see §1.4).

#### Capture trigger

After each completed **cast** reply (`channelKind=scene`, assistant/character role):

1. Build a **rolling window** snippet from recent **perceivable** scene lines ending with the new reply.
2. Append one segment per target character (§1.4).

Persona lines (`__persona__` or operator-as-persona) SHOULD appear in the snippet when they were perceivable at the scene. System lines, `channelKind=meta`, and lines the cast could not perceive MUST be excluded.

#### Snippet content (output-only)

Each line in the snippet MUST use `Name:\n{outputText}` (or equivalent attribution). Content MUST be **output-only** after `stripReasoning` ([16-learning.md](16-learning.md) MP-14–MP-17)—no reasoning, thinking, or hidden chain-of-thought.

**`diaryWindowSize`** (configurable, bounded e.g. 1–20, default ~4) controls how many recent perceivable non-system lines form the snippet. It bounds **snippet width**, not total diary history.

#### Retention vs injection

| Concern | Rule |
|---------|------|
| **Store** | Append-only segment list per `characterId`; no mandatory max segment count in v1. Operator compaction/export MAY be added later. |
| **Inject** | Mandatory recall and recall protocol use a **char budget** on the newest segments (~45% of `mandatoryRecallMaxChars`, capped by `diaryPreGenerationMaxChars`). |

Long retention with bounded inject preserves continuity after restart without unbounded prompt growth.

#### Capture hygiene (SHOULD)

- Skip in-flight streaming duplicates.
- Dedupe by hash of content + message id + swipe/generation id (`dedupeKey`).
- Suppress cold-load / greeting noise per operator policy (e.g. first message on world open only).

**Diary admin read:** Characters on `diaryAdminIds` MAY use a tool to read another character's diary. This MUST be allowlist-gated.

### 1.4 Group fan-out (MP-20)

When a diary segment is captured at scene `S`, the implementation MUST append the **same** segment (same `text`, `dedupeKey`, `sourceSceneId`, `messageIds`) to every **cast** `characterId` in `present` at `S`.

| Rule | Level |
|------|-------|
| Fan-out targets are present cast only (not muted elsewhere, not persona unless explicitly configured) | MUST |
| Whisper / DM lines excluded from snippet unless viewer would have perceived them | MUST |
| Persona token excluded from fan-out targets by default (diary is cast episodic memory) | SHOULD |
| Duplicate `dedupeKey` for a given `characterId` MUST NOT be written twice | MUST |

Rationale: everyone in the room heard the exchange; each character keeps their own diary store for privacy and recall assembly (MP-1 still applies to **mind** pool).

## 2. Recall protocol

The **recall protocol** is instructional text injected into the generation context (extension-prompt class) that tells the model:

1. Which pool to use for private vs shared facts.
2. To call memory tools before asserting non-dialogue facts.
3. **Tool budget** discipline.

### 2.1 Tool budget (normative)

| Rule | Level |
|------|-------|
| At most **one** `memory_search` per turn unless the prior search returned empty | SHOULD |
| Do not call `memory_read` twice on the same locus in one turn | SHOULD |
| Stop after two unproductive tool rounds | SHOULD |
| Before continuity claims, use `diary_search` / `diary_read` | SHOULD |

### 2.2 Protocol content

The recall protocol MUST include:

- Identity line: which character is speaking.
- Mind vs world definitions.
- Indexes of mind loci keys (and optional value previews up to `locusPreviewMaxChars`; **0 = keys only**, default SHOULD be 0 at scale).
- Indexes of world loci for the active scene.
- Optional injected **diary tail** (budgeted) in a fenced block.

## 3. Mandatory recall

**Mandatory recall** is a stronger, authoritative memory block injected at generation time (typically as a **system**-class message or equivalent high-priority slot).

Content (assembled in order, subject to char budget):

1. **Diary tail** (~45% of budget cap, also capped by `diaryPreGenerationMaxChars`) — **newest** segments first, stable ordering (MEM-ACC-2).
2. **Mind loci index** + up to 8 mind hits from **indexed** search over recent transcript lines for the **generating character only**.
3. **World loci index** for **active `sceneId` only**.
4. **Architect block** (optional): for diary admins, tails of other **present** characters' diaries (bounded per character).

Header MUST state that the character MUST treat diary and loci as **authoritative** unless new in-scene evidence contradicts them.

### 3.1 Per-generation scope (MEM-PERF-4)

| Rule | Level |
|------|-------|
| Mandatory recall assembled **only** for the generating `characterId` | MUST |
| Mind loci and diary queries filtered by that `characterId` | MUST |
| World loci filtered by active `sceneId` only | MUST |
| MUST NOT load or scan all cast memories on every turn | MUST |

### 3.1.1 Orchestrator speak-readiness (AO-17 exception)

The orchestrator MAY run a **bounded** FTS probe per eligible character **only** to pick the next speaker ([13-agent-orchestration.md](13-agent-orchestration.md) AO-17–AO-18). This is not mandatory recall assembly.

| Rule | Level |
|------|-------|
| Probe queries scoped to one `characterId` at a time | MUST |
| ≤8 characters probed per scheduling decision | MUST |
| Probe hits MUST NOT be written into other characters' prompts | MUST |
| Full mandatory recall for every present cast member on every scheduling tick | MUST NOT |

### 3.2 Assembly cache (MEM-PERF-3)

Implementations SHOULD cache assembled mandatory recall blocks:

| Field | Value |
|-------|-------|
| Cache key | `(characterId, sceneId, transcriptTailHash, configVersion)` |
| Invalidate on | Diary append, locus write, fixture sync, memory config change for that character/scene |
| Cold start (MP-11) | Rebuild from SQLite; cache optional |

**MEM-PERF-3:** P95 mandatory recall assembly on **cache miss** MUST be **&lt;100ms** excluding GPU (reference fixture in [17-acceptance-criteria.md](17-acceptance-criteria.md) §8).

### 3.3 Blocking mode

When **mandatory recall blocking** is enabled:

1. At generation start, only **memory tools** (`memory_*` prefix) are exposed to the model.
2. After the first memory tool invocation, the full tool set MAY be restored.
3. On generation end, the gate MUST reset.

Rationale: forces the model to ground in memory before web or filesystem tools.

### 3.4 Placement

| API style | Placement |
|-----------|-----------|
| Chat-completions with system messages | Prepend mandatory recall as system message; strip prior duplicate markers before re-inject |
| Legacy prompt assembly | Append to post-history world-info slot |

Duplicate injection MUST be prevented.

Configurable limits:

- `mandatoryRecallMaxChars` (e.g. 500–100000, default ~12000)
- `mandatoryRecallEnabled` (default on in roleplay presets)

Assembled block MUST NOT exceed `mandatoryRecallMaxChars` (MEM-ACC-5).

## 4. Memory tools

When tool calling is supported, the following tools SHOULD exist:

| Tool | Action |
|------|--------|
| `memory_store` | Append fact at locus; `pool`: mind \| world |
| `memory_read` | Read one locus |
| `memory_search` | Full-text search; `pool`: mind \| world \| both |
| `diary_read` | Paginated segments for self |
| `diary_search` | Newest-first search in self diary |
| `diary_read_other` | Read another character's diary (admin allowlist only) |

**Search semantics (v1):**

- **MEM-PERF-1:** Tool search MUST use an indexed full-text path (SQLite FTS5 or equivalent). Full table scans on `Locus` / `DiarySegment` are forbidden.
- **MEM-PERF-2:** P95 `memory_search` / `diary_search` latency MUST be **&lt;50ms** on the reference scale fixture ([17-acceptance-criteria.md](17-acceptance-criteria.md) §8).
- **Hybrid (v1, when embed index exists):** FTS ranks candidates first; semantic rerank of top-k when `EmbeddingRecord` rows exist ([00-inference-runtime.md](00-inference-runtime.md) INF-11). Substring/FTS remains the fallback when no embed row exists.
- Results truncated (e.g. 200 chars per hit) in tool output.
- **MEM-ACC-1:** Hybrid search MUST NOT return mind-pool rows for a different `characterId` (MP-1).

**Store validation:**

- `locus` trimmed non-empty.
- Mind store requires resolved `characterId`.
- World store requires active `sceneId`.

Memory tools do **not** use the approval queue (immediate effect).

## 5. Location fixture mirror

Scene **fixtures** and scene description MAY sync **one-way** into world pool loci (see [03-locations-and-presence.md](03-locations-and-presence.md)):

| Key pattern | Content |
|-------------|---------|
| `location:{sceneId}:__scene__` | `[SceneName] description` |
| `location:{sceneId}:{fixtureKey}` | Formatted fixture label, kind, state |

Prior keys with the same `location:{sceneId}:` prefix MUST be cleared before rewrite.

**Invariant (MP-2):** Mirror is one-way. Edits to world loci MUST NOT automatically mutate fixtures.

Sync SHOULD run when the active scene's metadata is flushed.

### 5.1 Briefing fixture mirror (post-v1)

Briefing fixtures ([23-in-world-work.md](23-in-world-work.md) §4) MAY sync one-way into world pool:

| Key pattern | Content |
|-------------|---------|
| `briefing:{sceneId}:{fixtureKey}` | Shared board text at that location |

Same one-way invariant as MP-2.

### 5.2 Provenance (MP-21, post-v1)

Facts stored from web, filesystem, or commission ingest SHOULD link an **EvidenceRecord** ([11-data-model.md](11-data-model.md) §3.15):

| Field | Purpose |
|-------|---------|
| `sourceKind` | `dialogue` \| `web` \| `file` \| `operator` |
| `sourceRef` | URL, path, or `messageId` |
| `retrievedAt` | ISO timestamp |

Operator memory inspector shows provenance. In-character prompts cite sources only when world config `citeProvenanceInPrompt` is enabled.

## 6. Storage and migration

### 6.1 Storage scopes

| Data | Key |
|------|-----|
| Mind loci | `characterId` |
| Diary | `characterId` |
| World loci | `sceneId` |
| Commons loci | `worldId` |
| Settings | Operator / world config |

Persistence: SQLite per [11-data-model.md](11-data-model.md). Implement via `PersistencePort` in `backend/altrasia/persistence/` (indexes + FTS5 in migration 001).

### 6.2 Legacy migration

If a flat `loci` map existed without pool split, on load the implementation SHOULD:

1. Merge into active scene world pool, or
2. Hold in `pendingWorldMerge` until a scene is active.

## 7. Conflicts with vector RAG

If the platform also injects **vector-retrieved** chat chunks as episodic memory, operators SHOULD disable overlapping injection. **Diary + mandatory recall** are the canonical episodic path; duplicate RAG risks contradiction and token waste.

Embeddings assist **tool search** only; they MUST NOT replace diary tails or mandatory recall injection (INF-9).

## 8. External memory systems (out of scope)

Altrasia MUST NOT depend at runtime on:

- [MemPalace/mempalace](https://github.com/mempalace/mempalace) (GitHub)
- Mem0, Zep, Letta, or similar agent-memory SaaS as the primary memory backend

Optional post-v1 **reflection** jobs MAY propose `memory_store` mind loci with operator approval ([16-learning.md](16-learning.md) §6).

## 9. Requirements summary

| ID | Requirement |
|----|-------------|
| MP-1 | Mind pool never leaks to other characters. |
| MP-2 | Fixture mirror is one-way into world pool. |
| MP-3 | Locus store appends unless operator overwrite API exists. |
| MP-4 | Recall protocol includes pool semantics and tool budget. |
| MP-5 | Mandatory recall is authoritative; blocking mode restricts tools until memory tool used. |
| MP-6 | Diary capture dedupes; snippets are witnessed perceivable scene dialogue (output-only), not assistant monologue-only. |
| MP-7 | `diary_read_other` requires diary admin allowlist. |
| MP-20 | On capture at scene S, fan-out the same segment to every present cast `characterId` (§1.4). |
| MEM-PERF-1 | Indexed FTS for tool search; no full table scans. |
| MEM-PERF-2 | P95 tool search &lt;50ms on reference fixture. |
| MEM-PERF-3 | P95 mandatory recall assembly (cache miss) &lt;100ms. |
| MEM-PERF-4 | Recall scoped to generating character + active scene only. |
| MEM-ACC-1 | Hybrid search respects MP-1. |
| MEM-ACC-2 | Diary tail = newest segments within budget, stable order. |
| MEM-ACC-3 | `memory_store` append-only unless operator overwrite API. |
| MEM-ACC-4 | Golden-path restart continuity ([17-acceptance-criteria.md](17-acceptance-criteria.md)). |
| MEM-ACC-5 | Assembled mandatory recall ≤ `mandatoryRecallMaxChars`. |
| MP-21 | External facts from web/FS/commission SHOULD attach EvidenceRecord provenance. |
| MP-22 | World commons recall gated by `commonsAccessIds`; no MP-1 violation. |

Extended requirements **MP-8–MP-19** (universal memory discipline, output-only storage, `stripReasoning`) are defined in [16-learning.md](16-learning.md).

## Related documents

- [03-locations-and-presence.md](03-locations-and-presence.md) — fixtures and scene metadata
- [05-tool-calling.md](05-tool-calling.md) — tool invoke loop
- [10-prompt-injection.md](10-prompt-injection.md) — placement of recall blocks
- [11-data-model.md](11-data-model.md) — SQLite schema, indexes, FTS5
- [16-learning.md](16-learning.md) — MP-8–MP-19, stripReasoning
- [17-acceptance-criteria.md](17-acceptance-criteria.md) — performance benchmarks
- [23-in-world-work.md](23-in-world-work.md) — commissions, debate, briefing fixtures
