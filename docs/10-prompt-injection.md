# 10 — Prompt Injection

Altrasia assembles the model context from **layers** with defined priority, placement, and refresh triggers. This document specifies those layers—not provider-specific preset names.

## 1. Layer stack

From highest authority (typical) to lowest for factual grounding:

| Order | Layer | Class | Source |
|-------|-------|-------|--------|
| 1 | System / developer instructions | system | Character card, world rules |
| 2 | **Mandatory recall** | system | [02-memory.md](02-memory.md) |
| 3 | **Recall protocol** | system or in-prompt | Memory indexes + tool budget |
| 4 | **Scene framing** | in-prompt | [03-locations-and-presence.md](03-locations-and-presence.md) |
| 5 | Observer digest | in-prompt | [09-roles-and-privilege.md](09-roles-and-privilege.md) |
| 6 | Transcript | user/assistant | Scene messages (perception filtered) |
| 7 | World info / lorebooks | variable | Optional; avoid contradicting mandatory recall |

**Requirement (PI-1):** Before each generation, strip prior copies of the same inject marker (e.g. `[ Memory — mandatory recall ]`) to prevent duplication on regenerate/swipe.

## 2. Mandatory recall placement

| API style | Placement |
|-----------|-----------|
| Chat completions (system messages) | Prepend as system message |
| Legacy single-string prompt | Append to post-history slot equivalent to "after chat" |

Only one path MUST run per generation (detect API style and choose one).

Configurable:

- `mandatoryRecallEnabled`
- `mandatoryRecallMaxChars`
- `diaryPreGenerationMaxChars`

## 3. Recall protocol placement

Extension-prompt slot (configurable):

| Setting | Typical value |
|---------|---------------|
| `position` | In prompt (not post-history only) |
| `depth` | Shallow (e.g. 2) |
| `role` | system |
| `scan` | true (re-evaluate each generation) |

Content built from: mind/world indexes, optional diary tail fence, tool budget lines, speaking character label.

Refresh when: scene changes, loci change, diary append, member drafted.

## 4. Scene framing placement

Per **drafted character** at generation time:

- Key: e.g. `scene_framing`
- Only if character is present at a scene
- Includes scene title, description, fixtures, present inventories

Settings mirror recall protocol: position, depth, role, scan, `sceneFramingEnabled`.

Refresh on: `scene.changed`, `presence.changed`, `world.member_drafted`.

## 5. Perception-filtered transcript

Assembled transcript MUST use `canPerceive(viewer)` per message ([04-communication.md](04-communication.md)).

Phone mirrors and whispers omitted for non-participants.

## 6. Refresh trigger matrix

| Event | Mandatory recall | Recall protocol | Scene framing |
|-------|------------------|-----------------|---------------|
| Scene switch | Rebuild | Rebuild | Rebuild |
| Presence change | Rebuild | Rebuild | Rebuild |
| Loci store | — | Rebuild | — |
| Diary append | Rebuild | Rebuild | — |
| Member drafted | Rebuild | Rebuild | Rebuild for that character |
| Swipe/regenerate | Strip + inject | Strip + inject | Rebuild |

## 7. Token budgeting

1. Reserve tool schema tokens early in budget calculation.
2. Mandatory recall fills up to cap; diary and loci subdivisions use internal ratios (e.g. ~45% diary in recall bundle).
3. Scene framing SHOULD be concise; fixture list may truncate with "and N more".

## 8. Blocking mode interaction

When mandatory recall blocking active ([02-memory.md](02-memory.md)):

- Tool registration filter runs **after** prompt assembly
- Only `memory_*` tools until first memory invocation

## 9. Requirements summary

| ID | Requirement |
|----|-------------|
| PI-1 | Dedupe inject markers each generation. |
| PI-2 | Mandatory recall and recall protocol stay consistent with transcript. |
| PI-3 | Scene framing scoped to drafted character's presence. |
| PI-4 | Transcript filtered by communication perception. |
| PI-5 | One mandatory-recall injection path per API style. |

## Related documents

- [02-memory.md](02-memory.md)
- [03-locations-and-presence.md](03-locations-and-presence.md)
- [04-communication.md](04-communication.md)
