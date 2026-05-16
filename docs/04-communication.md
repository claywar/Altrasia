# 04 — Communication

WorldEngine tags messages with **communication scope** so prompts, UI, and tools know who can perceive each line. Scopes interact with **presence** at the active scene and optional **cross-scene phone** links.

## 1. Scope matrix

| Scope | Metadata value | Default audience | Prompt filter |
|-------|----------------|------------------|---------------|
| **Public** | `public` | All characters **present** at active scene | Everyone at scene |
| **Whisper** | `whisper` | `participants` + speaker | Listed participants only |
| **Phone** | `phone` | Near-end participants; mode-dependent | Per phone mode |
| **DM** | `dm` | Explicit `participants` | Listed participants only |

Metadata lives on each message, e.g. `message.meta.communication`:

```json
{
  "scope": "whisper",
  "participants": ["char-alice-id"],
  "phone": { "mode": "handset", "channelId": "..." }
}
```

## 2. Phone modes

| Mode | Who hears in assembled prompt | Room overhear |
|------|--------------------------------|---------------|
| **handset** | Speaker + remote party + present at speaker's scene | No full-room broadcast |
| **speakerphone** | Above + all present at **both** linked scenes | Effectively public at both ends |

**Channels** are stored per world: `activeChannels[]` with endpoints (scene ids, participant ids). A mirror copy SHOULD sync to world aggregate for external roster APIs.

## 3. Cross-scene phone mirrors

Canonical phone/whisper lines live on the **speaker's active scene** transcript.

**Mirror stubs** MAY append to other participants' scene transcripts with:

```json
{
  "communication": {
    "mirrorOf": {
      "sceneId": "...",
      "messageIndex": 42,
      "canonicalId": "..."
    }
  }
}
```

Mirrors exist for operator visibility and continuity; perception filters MUST still apply per viewer.

## 4. Perception filter

Before prompt assembly, each message passes through **canPerceive(viewer, message)**:

1. Resolve viewer's `characterId` (or persona rules).
2. Read `message.meta.communication`.
3. Return include/exclude for prompt and optional UI dimming.

Hook/event equivalent: `message.perceive_filter` with `{ viewerId, message, include }`.

Legacy fallback: callback `shouldIncludeMessageForViewer` if no listeners registered.

### 4.1 Generation member filter

**Group generation** SHOULD filter which characters are eligible to reply:

- Default: present at active scene.
- Optional: include phone participants from linked channel when `phone_participants_eligible` is true.
- Same filter MAY apply to `getWorldMembers()` when `filter_members_by_presence` is enabled.

## 5. Operator compose

The operator UI SHOULD offer scope selector above send: public / whisper / phone.

`sendScopedMessage(world, scene, { scope, text, targetCharacterId })` attaches metadata before append.

Badges on messages indicate scope; non-audible lines MAY render dimmed for current viewer.

## 6. Tools and commands

Slash or natural commands (implementation-defined):

| Command | Effect |
|---------|--------|
| `/whisper Target \| text` | Whisper to target |
| `/phone Target \| text` | Start/continue phone |
| `/phone-end` | End channel |
| `/phone-speaker` | Toggle speakerphone |
| `/dm A B \| text` | Direct message |

LLM tools example: `comm_whisper`, `comm_phone` — whisper MAY send immediately when `text` provided, else open compose UI only.

## 7. Narrative detection integration

When narrative presence is in `auto` or `llm` mode, detected whispers and phone answers SHOULD set appropriate scope metadata and MAY trigger join/leave side effects (see [03-locations-and-presence.md](03-locations-and-presence.md)).

## 8. Requirements summary

| ID | Requirement |
|----|-------------|
| C-1 | Every operator-originated line SHOULD have explicit scope metadata. |
| C-2 | Public scope audience = present at active scene only. |
| C-3 | Perception filter runs before prompt assembly per viewer. |
| C-4 | Phone speakerphone includes both scenes' present casts. |
| C-5 | Cross-scene mirrors reference canonical message. |
| C-6 | Generation eligibility respects presence + optional phone rules. |

## Related documents

- [03-locations-and-presence.md](03-locations-and-presence.md) — present roster
- [09-roles-and-privilege.md](09-roles-and-privilege.md) — persona speak guards
- [05-tool-calling.md](05-tool-calling.md) — communication tools
