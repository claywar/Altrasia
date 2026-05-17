# 09 — Roles and Privilege

WorldEngine separates **in-fiction knowledge** from **operator affordances**. Roles configure who may administer scenes, read private diaries, observe all locations, and act on the real world.

## 1. Role overview

| Role | Typical holders | Capabilities |
|------|-----------------|--------------|
| **Cast member** | Story characters | Mind memory, scene presence, scoped comms |
| **Persona** | Human operator | Presence, public/whisper/DM send; v1.1 phone |
| **Location admin** | Observer (default v1) | Scene CRUD, summon, fixture admin tools |
| **Diary admin** | Observer (optional) | `diary_read_other`, architect recall block |
| **Observer** | Meta character | World control, digest, narrator/deus ex modes |
| **Architect** | Optional split | FS tools, schedules (Phase 4+; MAY merge into Observer in v1) |

Roles are **allowlists of `characterId`**, not hierarchical RBAC unless extended.

v1 single-operator worlds SHOULD grant Observer **location admin** by default (OBS-3). Architect capabilities MAY be disabled until Phase 4.

## 2. Observer

### 2.1 Purpose

The Observer is the operator's **control surface** for running the world: multi-scene awareness, studio side-chat, and optional in-fiction **narrator** / **deus ex** modes—not a passive digest-only role.

Cast characters MUST NOT gain facts from the Observer digest unless communicated in play (ROLE-1).

### 2.2 Observer modes

| Mode | Purpose | Channel |
|------|---------|---------|
| **Watch** | Digest, queue, tool trace | No speech |
| **Narrate** | Scene-setting prose | `channelKind=scene`, scope `narrator` |
| **Intervene** | Deus ex via tools | `channelKind=scene` + tools |
| **Direct** | Operator-directed generation | Meta or scene per UI |

Mode is set on `GenerationJob.observerMode` or Web UI ([14-web-ui.md](14-web-ui.md)).

### 2.3 Observer capabilities

| ID | Requirement |
|----|-------------|
| OBS-1 | Observer is a real `characterId` with mind pool and diary (MP-1 applies to other minds). |
| OBS-2 | Observer is default executor for world-mutating Web UI actions unless persona uses direct tools. |
| OBS-3 | Observer SHOULD hold location admin (and optionally diary admin) in v1 single-operator worlds. |
| OBS-4 | Narrator uses scope `narrator` ([04-communication.md](04-communication.md)); perceivable at scene; not cast private knowledge unless witnessed and stored. |
| OBS-5 | Durable state changes MUST use tools (`scene_*`, `memory_store` world pool, approvals)—not free-text assertion. |
| OBS-6 | Digest is operator affordance; includes pending signals (CC-6). |
| OBS-7 | Observer in scheduler when operator requests modes; excluded from ambient idle NPC by default. |
| OBS-8 | Observer MAY author **in-map** locations (new scenes, exits, layout) when operator directs; layout changes require MapDraft preview + ack ([25-map-authoring.md](25-map-authoring.md) MAP-GROW-1). Cast MUST NOT author geography. |

### 2.4 Observer digest

When `observerDigestMultiScene` is enabled, generation for Observer MAY include:

- All scenes: name, present count, fixture preview
- Worn/container summaries for present cast
- Pending `CrossSceneSignal` and channel summary

**Diegesis rule (ROLE-1):** Digest is not in-character knowledge for cast unless rules in §2.1 apply.

Observer MAY use digest for planning but MUST still run memory tools before stating continuity facts as narrator (MP-8–MP-10).

**Diegesis rule (ROLE-6, post-v1):** World **commons** loci and **briefing fixture** mirrors are institutional or room-visible records—not telepathy. Cast treat commons as known in dialogue only after witnessed briefing (public line, perceivable board at scene, or narrator). Commission status in operator UI is not cast knowledge until stored in mind pool or communicated in play (COM-1–COM-2).

### 2.5 Meta channel (Observer Studio)

Operator ↔ Observer tuning uses `channelKind=meta` ([11-data-model.md](11-data-model.md)):

- Excluded from cast `canPerceive` and prompt assembly
- MP-8–MP-9 apply when Observer asserts world facts
- API: meta-messages routes ([12-api-sketch.md](12-api-sketch.md))

### 2.6 Primary observer

One `primaryObserverId` SHOULD be listed first in roster APIs.

### 2.7 Sync with diary admin

When `syncMempalaceObservers` is enabled, diary admin ids merge into observer allowlists.

## 3. Location admin

`locationAdminIds` + `primaryObserverId` gate:

- `scene_location_create`, rename, delete
- `scene_summon`, force join/leave
- Destructive fixture operations

## 4. Diary admin

`diaryAdminIds` grants:

- Tool `diary_read_other`
- Optional extra diary tails in mandatory recall for present characters

Does not grant filesystem write.

## 5. Architect

Phase 4+ real-world tools ([08-real-world-capabilities.md](08-real-world-capabilities.md)). v1 MAY omit or fold into Observer tool profile.

## 6. Persona rules

| Setting | Effect |
|---------|--------|
| `requirePersonaPresentToSpeak` | Block/warn public send if persona not in active scene present list |
| `personaAutoJoinOnSceneSwitch` | Auto-add persona token to present on scene switch |

Persona row in roster UI: **Here** / **Watching only** / **Away**.

## 7. Muted and disabled

| Flag | Effect |
|------|--------|
| **Muted** | In present list but filtered from generation |
| **Disabled member** | World member excluded from default generation lists |

## 8. World activity exclusions

Idle/reactive NPC selection MUST exclude:

- Persona token
- Observer ids (configurable)
- Location admin ids (optional)
- Muted/disabled

## 9. Universal memory discipline

All roles that generate—including Observer—MUST follow MP-8–MP-19 ([02-memory.md](02-memory.md), [16-learning.md](16-learning.md)):

- Mandatory recall default on
- Blocking mode default on (memory tools first)
- Output-only durable memory
- Cold-start hydrate from SQLite (MP-11)

## 10. Requirements summary

| ID | Requirement |
|----|-------------|
| ROLE-1 | Observer digest is not in-character knowledge by default. |
| ROLE-2 | Diary admin gates `diary_read_other`. |
| ROLE-3 | Location admin gates scene CRUD tools. |
| ROLE-4 | Architect gates FS and scheduler (when enabled). |
| ROLE-5 | Persona presence rules enforced when configured. |
| ROLE-6 | Commons and briefing boards are not in-character knowledge until witnessed or communicated (post-v1). |
| OBS-1–OBS-7 | Observer control surface and modes. |

## Related documents

- [03-locations-and-presence.md](03-locations-and-presence.md)
- [02-memory.md](02-memory.md)
- [04-communication.md](04-communication.md)
- [14-web-ui.md](14-web-ui.md)
- [16-learning.md](16-learning.md)
- [23-in-world-work.md](23-in-world-work.md)
