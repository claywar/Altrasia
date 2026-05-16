# 09 — Roles and Privilege

WorldEngine separates **in-fiction knowledge** from **operator affordances**. Roles configure who may administer scenes, read private diaries, observe all locations, and act on the real world.

## 1. Role overview

| Role | Typical holders | Capabilities |
|------|-----------------|--------------|
| **Cast member** | Story characters | Mind memory, scene presence, scoped comms |
| **Persona** | Human operator | Presence, public/whisper/phone send, optional speak guard |
| **Location admin** | Trusted character ids | Scene CRUD, summon, fixture admin tools |
| **Diary admin** | Observer, Architect | `diary_read_other`, architect recall block |
| **Observer** | Meta character | Multi-scene digest; excluded from idle NPC pools |
| **Architect** | Builder character | FS tools, schedules, character admin |

Roles are **allowlists of `characterId`**, not hierarchical RBAC unless extended.

## 2. Observer

### 2.1 Purpose

Observers maintain **cross-scene situational awareness** for the operator and meta agents without implying every character knows what the observer knows.

### 2.2 Observer digest

When `observerDigestMultiScene` is enabled, generation for observer-class characters MAY include:

- All scenes: name, present count, fixture preview
- Worn/container summaries for present cast

**Diegesis rule (ROLE-1):** Digest text is a **model affordance**. In-fiction characters MUST NOT gain facts from the digest unless:

1. Another character communicated it in visible transcript, or
2. The operator issued an explicit instruction naming who may know what.

### 2.3 Primary observer

One `primaryObserverId` SHOULD be listed first in roster APIs and excluded from "absent/not involved" buckets to avoid duplicate listing.

### 2.4 Sync with diary admin

When `syncMempalaceObservers` is enabled, **diary admin ids** merge into observer allowlists for roster and digest behavior.

## 3. Location admin

`locationAdminIds` + `primaryObserverId` gate:

- `scene_location_create`, rename, delete
- `scene_summon`, force join/leave
- Destructive fixture operations

Non-admins MAY still use narrative presence auto-join or self-service join if policy allows.

## 4. Diary admin

`diaryAdminIds` grants:

- Tool `diary_read_other`
- Optional extra diary tails in **mandatory recall** for present characters
- Sync into observer list (optional)

Does not grant filesystem write.

## 5. Architect

`architectIds` (e.g. `Architect` character):

- Filesystem tools (server enabled)
- Scheduled task tools (scheduler enabled)
- Character list/create/update
- SHOULD appear in diary admin list

Prompt snippet MUST cover approval discipline and memory tool budgets.

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

Muted characters MAY still appear in scene framing lists with visual distinction.

## 8. World activity exclusions

Idle/reactive NPC selection MUST exclude:

- Persona token
- Observer ids (configurable)
- Location admin ids (optional, for ambient scenes)
- Muted/disabled

## 9. Requirements summary

| ID | Requirement |
|----|-------------|
| ROLE-1 | Observer digest is not in-character knowledge by default. |
| ROLE-2 | Diary admin allowlist gates cross-character diary reads. |
| ROLE-3 | Location admin gates scene CRUD tools. |
| ROLE-4 | Architect allowlist gates FS and scheduler tools. |
| ROLE-5 | Persona presence rules enforced when configured. |

## Related documents

- [03-locations-and-presence.md](03-locations-and-presence.md)
- [02-memory-palace.md](02-memory-palace.md)
- [08-real-world-capabilities.md](08-real-world-capabilities.md)
