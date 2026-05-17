# 12 — API Sketch

REST and realtime surfaces for WorldEngine v1 (single-operator). This is a sketch, not a full OpenAPI document.

**Single domain path:** Web UI actions, agent tools, narrative presence ([03-locations-and-presence.md](03-locations-and-presence.md) §7), and future scheduled jobs MUST call the same core services (presence, comms, memory, scene CRUD)—not parallel state machines with divergent rules.

## 1. Transport

| Mechanism | Use |
|-----------|-----|
| REST | CRUD, commands |
| WebSocket or SSE | Events (`generation.*`, `scene.changed`, `queue.updated`) |
| SSE | Optional dedicated generation stream per job |

Auth v1: session cookie or `Authorization: Bearer` from env (`WORLDENGINE_API_TOKEN`).

All world-scoped routes assume one operator; no multi-tenant headers.

## 2. Conventions

- Base path: `/api/v1`
- IDs are opaque strings (UUID recommended)
- Errors: `{ "error": { "code", "message" } }`
- Timestamps: ISO 8601 UTC
- Per-world **`eventSeq`** monotonic integer on WS events for reconnect ([11-data-model.md](11-data-model.md))

## 3. Worlds and scenes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/worlds` | List worlds |
| POST | `/worlds` | Create world (wizard payload) |
| GET | `/worlds/{worldId}` | World detail + active scene |
| PATCH | `/worlds/{worldId}` | Update name, activeSceneId, config |
| GET | `/worlds/{worldId}/scenes` | List scenes |
| POST | `/worlds/{worldId}/scenes` | Create scene |
| GET | `/worlds/{worldId}/scenes/{sceneId}` | Scene header + presence |
| PATCH | `/worlds/{worldId}/scenes/{sceneId}` | Rename, description, exits |
| DELETE | `/worlds/{worldId}/scenes/{sceneId}` | Reject if last scene (W-1) |

## 4. Messages and compose

| Method | Path | Description |
|--------|------|-------------|
| GET | `/worlds/{worldId}/scenes/{sceneId}/messages` | Scene transcript (`channelKind=scene`) |
| POST | `/worlds/{worldId}/scenes/{sceneId}/messages` | Persona send; body includes `scope`, `text` |
| GET | `/worlds/{worldId}/observer/meta-messages` | Observer Studio thread |
| POST | `/worlds/{worldId}/observer/meta-messages` | Operator → Observer meta chat |

**POST message body (scene):**

```json
{
  "text": "Hello?",
  "scope": "public",
  "participants": ["char-bob"],
  "asPersona": true
}
```

Scopes v1: `public`, `whisper`, `dm`. v1.1 adds `phone` ([21-cross-scene-awareness.md](21-cross-scene-awareness.md)).

## 5. Presence

| Method | Path | Description |
|--------|------|-------------|
| POST | `/worlds/{worldId}/scenes/{sceneId}/presence/join` | `{ "characterId" }` |
| POST | `/worlds/{worldId}/scenes/{sceneId}/presence/leave` | `{ "characterId" }` |
| POST | `/worlds/{worldId}/presence/summon` | `{ "characterIds", "targetSceneId" }` |
| GET | `/worlds/{worldId}/roster` | Buckets: atLocation, elsewhere, muted, unplaced |

## 6. Cross-scene (v1 tracking)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/worlds/{worldId}/spatial-graph` | Scenes, exits, elsewhere roster |
| GET | `/worlds/{worldId}/signals` | Pending CrossSceneSignals |
| POST | `/worlds/{worldId}/signals` | Create knock/ring/buzz |
| PATCH | `/worlds/{worldId}/signals/{signalId}` | acknowledge / expire |

v1.1: `/worlds/{worldId}/channels`, phone send; `PATCH .../channels/{id}/endpoints/{sceneId}` body `{ "speakerphone": true }` ([04-communication.md](04-communication.md) §3.4).

## 7. Generation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/worlds/{worldId}/generate` | Enqueue GenerationJob |
| GET | `/worlds/{worldId}/queue` | Agent + GPU queue snapshot |
| POST | `/worlds/{worldId}/pause` | Pause world activity |
| POST | `/worlds/{worldId}/resume` | Resume |
| DELETE | `/inference/queue/{jobId}` | Cancel GPU job (INF-5g) |
| GET | `/worlds/{worldId}/generations/{jobId}/stream` | SSE token stream (STR-*) |

**POST generate body:**

```json
{
  "characterId": "observer",
  "sceneId": "scene-kitchen",
  "trigger": "operator",
  "observerMode": "Direct",
  "prompt": "Rename this scene to Pantry."
}
```

## 8. Observer

| Method | Path | Description |
|--------|------|-------------|
| GET | `/worlds/{worldId}/observer/digest` | Multi-scene digest (OBS-6) |
| POST | `/worlds/{worldId}/observer/generate` | Observer generation with `observerMode` |

## 9. Memory (operator)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/characters/{characterId}/loci` | Mind pool (operator) |
| GET | `/scenes/{sceneId}/loci` | World pool |
| GET | `/characters/{characterId}/diary` | Diary segments |
| PATCH | `/characters/{characterId}/loci/{key}` | Operator overwrite (optional) |

Agent tools (`memory_*`, `diary_*`) use internal paths during generation ([02-memory.md](02-memory.md)).

## 10. Approvals

| Method | Path | Description |
|--------|------|-------------|
| GET | `/approvals` | Pending list |
| POST | `/approvals/{approvalId}/approve` | |
| POST | `/approvals/{approvalId}/deny` | |

## 11. Inference health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health/llm` | Primary up |
| GET | `/health/embeddings` | Embed up |
| GET | `/inference/queue` | INF-5f global queue |

## 12. WebSocket events

Subscribe: `WS /api/v1/worlds/{worldId}/events`

| Event | Payload |
|-------|---------|
| `scene.changed` | sceneId |
| `presence.changed` | sceneId, characterId, action |
| `generation.token` | jobId, messageId, delta |
| `generation.tool_call` | jobId, tools |
| `generation.done` | jobId, messageId |
| `generation.error` | jobId, code, message |
| `approval.updated` | approvalId, state |
| `queue.updated` | busy, depth, currentJob |
| `signal.created` | signalId, targetSceneId |

Client on reconnect: `GET` snapshot (world, active scene, roster, queue) then apply events where `eventSeq > lastSeen`.

## 13. Requirements summary

| ID | Requirement |
|----|-------------|
| API-1 | REST + WS/SSE for v1 operator console |
| API-2 | Meta messages isolated from scene transcript routes |
| API-3 | Streaming endpoint or WS tokens for STR-* |
| API-4 | Per-world eventSeq for ordering |

## Related documents

- [11-data-model.md](11-data-model.md)
- [14-web-ui.md](14-web-ui.md)
- [00-inference-runtime.md](00-inference-runtime.md)
