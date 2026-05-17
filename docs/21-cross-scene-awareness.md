# 21 — Cross-Scene Awareness

Cross-scene interaction (door knock, phone, speakerphone) is a **core product promise**. v1 **tracks** state; v1.1 **implements** play.

## 1. Phasing

```mermaid
flowchart LR
  subgraph v1 [v1 Track]
    Adj[exits]
    Roster[elsewhere]
    Sig[signals]
    Schema[comm schema]
  end
  subgraph v11 [v1.1 Play]
    Phone[phone]
    Mirror[mirrors]
    Gen[phone gen]
  end
  v1 --> v11
```

## 2. v1 — track and surface (CC-1–CC-7)

| ID | Requirement |
|----|-------------|
| CC-1 | `exits[]` on each scene: exitId, label, targetSceneId, kind (`door` \| `path` \| `portal`). |
| CC-2 | `CrossSceneSignal`: knock \| ring \| buzz; status pending \| acknowledged \| expired; durable. |
| CC-3 | Elsewhere roster includes `presentSceneId`. |
| CC-4 | `activeChannels[]` shape reserved; empty in v1. |
| CC-5 | Message `meta.communication` supports `phone`; UI/tools disabled until v1.1. |
| CC-6 | Observer digest lists pending signals and channel summary. |
| CC-7 | `canPerceive` extensible; v1 implements public, whisper, DM, narrator only. |

### v1 operator affordances

- "Knock on [exit]" → `CrossSceneSignal`
- Target scene banner: "Someone knocks"
- No auto phone conversation until v1.1

API: [12-api-sketch.md](12-api-sketch.md) spatial-graph and signals routes.

## 3. v1.1 — implement play (CC-8–CC-13)

| ID | Requirement |
|----|-------------|
| CC-8 | **Handset (default):** call participants hear both sides; present bystanders hear **one side** only (local `speakerSceneId`) per C-8, C-9. |
| CC-9 | **Speakerphone:** optional **per endpoint**; when on at a scene, present bystanders there hear both sides; other end unaffected per C-10, C-11. |
| CC-10 | Mirror stubs on remote transcript with `mirrorOf` ref; mirrors obey same perception rules ([04-communication.md](04-communication.md) §4). |
| CC-11 | Knock answer may enqueue generation or join/channel. |
| CC-12 | AO-2 phone/knock triggers enabled. |
| CC-13 | Persona compose: phone + **per-scene** speakerphone toggle. |

## 4. Perception (v1)

`canPerceive(viewer, message)` MUST handle:

| scope | v1 |
|-------|-----|
| `public` | Present at scene |
| `whisper` | participants + speaker |
| `dm` | participants |
| `narrator` | Present at scene |
| `phone` | Parse only; exclude until v1.1; then C-4–C-11 / CC-8–CC-9 |

Messages with `channelKind=meta` MUST return false for all cast viewers.

## 5. Narrator scope

Added in [04-communication.md](04-communication.md): omniscient description at scene, not meta channel.

## 6. Explicit v1 non-goals

- Live phone conversation
- Mirror append to remote scenes
- Speakerphone
- Cross-scene generation eligibility

## 7. Requirements summary

| ID | Phase |
|----|-------|
| CC-1–CC-7 | v1 |
| CC-8–CC-13 | v1.1 |

## Related documents

- [04-communication.md](04-communication.md)
- [03-locations-and-presence.md](03-locations-and-presence.md)
- [11-data-model.md](11-data-model.md)
- [17-acceptance-criteria.md](17-acceptance-criteria.md)
