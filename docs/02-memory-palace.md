# 02 — Memory Palace

The **Memory Palace** is WorldEngine's structured memory layer: method-of-loci **facts**, **pools** with strict privacy, an episodic **diary**, and prompt-time **recall** so characters answer consistently without leaking private knowledge.

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
- Indexes of mind loci keys (and optional value previews up to `locusPreviewMaxChars`; 0 = keys only).
- Indexes of world loci for the active scene.
- Optional injected **diary tail** (budgeted) in a fenced block.

## 3. Mandatory recall

**Mandatory recall** is a stronger, authoritative memory block injected at generation time (typically as a **system**-class message or equivalent high-priority slot).

Content (assembled in order, subject to char budget):

1. **Diary tail** (~45% of budget cap, also capped by `diaryPreGenerationMaxChars`).
2. **Mind loci index** + up to 8 mind hits from substring search over recent transcript lines.
3. **World loci index** for active scene.
4. **Architect block** (optional): for diary admins, tails of other **present** characters' diaries (bounded per character).

Header MUST state that the character MUST treat diary and loci as **authoritative** unless new in-scene evidence contradicts them.

### 3.1 Blocking mode

When **mandatory recall blocking** is enabled:

1. At generation start, only **memory tools** (`memory_*` prefix) are exposed to the model.
2. After the first memory tool invocation, the full tool set MAY be restored.
3. On generation end, the gate MUST reset.

Rationale: forces the model to ground in memory before web or filesystem tools.

### 3.2 Placement

| API style | Placement |
|-----------|-----------|
| Chat-completions with system messages | Prepend mandatory recall as system message; strip prior duplicate markers before re-inject |
| Legacy prompt assembly | Append to post-history world-info slot |

Duplicate injection MUST be prevented.

Configurable limits:

- `mandatoryRecallMaxChars` (e.g. 500–100000, default ~12000)
- `mandatoryRecallEnabled` (default on in roleplay presets)

## 4. Memory tools

When tool calling is supported, the following tools SHOULD exist:

| Tool | Action |
|------|--------|
| `memory_store` | Append fact at locus; `pool`: mind \| world |
| `memory_read` | Read one locus |
| `memory_search` | Substring search; `pool`: mind \| world \| both |
| `diary_read` | Paginated segments for self |
| `diary_search` | Newest-first search in self diary |
| `diary_read_other` | Read another character's diary (admin allowlist only) |

**Search semantics:**

- Case-insensitive substring on keys and values.
- Results truncated (e.g. 200 chars per hit) in tool output.

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

## 6. Storage and migration

### 6.1 Storage scopes

| Data | Key |
|------|-----|
| Mind loci | `characterId` |
| Diary | `characterId` |
| World loci | `sceneId` |
| Settings | Operator / world config |

### 6.2 Legacy migration

If a flat `loci` map existed without pool split, on load the implementation SHOULD:

1. Merge into active scene world pool, or
2. Hold in `pendingWorldMerge` until a scene is active.

## 7. Conflicts with vector RAG

If the platform also injects **vector-retrieved** chat chunks as episodic memory, operators SHOULD disable overlapping injection. **Diary + mandatory recall** are the canonical episodic path; duplicate RAG risks contradiction and token waste.

## 8. Requirements summary

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

Extended requirements **MP-8–MP-19** (universal memory discipline, output-only storage, `stripReasoning`) are defined in [16-learning.md](16-learning.md).

## Related documents

- [03-locations-and-presence.md](03-locations-and-presence.md) — fixtures and scene metadata
- [05-tool-calling.md](05-tool-calling.md) — tool invoke loop
- [10-prompt-injection.md](10-prompt-injection.md) — placement of recall blocks
- [16-learning.md](16-learning.md) — MP-8–MP-19, stripReasoning
