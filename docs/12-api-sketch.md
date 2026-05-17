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
| POST | `/worlds` | Create world (wizard payload or `{ "fixtureId": "demo-spatial-v1" }`) |
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

**Presentation (Web UI):** `text` is stored as plain string; MAY include markdown and fenced `mermaid` blocks. Optional request field `contentFormat: "markdown"` is a hint for compose preview only—persistence unchanged. Rendering rules: [14-web-ui.md](14-web-ui.md) UI-R1–R7. Committed messages MUST NOT be deleted via API (UI-TRN-1).

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
| GET | `/worlds/{worldId}/spatial-graph` | Scenes, exits, computed layout for mini-map ([14-web-ui.md](14-web-ui.md) UI-MAP-D*) |
| GET | `/worlds/{worldId}/signals` | Pending CrossSceneSignals |
| POST | `/worlds/{worldId}/signals` | Create knock/ring/buzz |
| PATCH | `/worlds/{worldId}/signals/{signalId}` | Body `{ "status": "acknowledged" \| "expired" }` — does not enqueue generation (CC-11b) |
| POST | `/worlds/{worldId}/signals/{signalId}/answer` | **v1.1** — explicit answer; MAY enqueue generation or join (CC-11) |

v1.1: `/worlds/{worldId}/channels`, phone send; `PATCH .../channels/{id}/endpoints/{sceneId}` body `{ "speakerphone": true }` ([04-communication.md](04-communication.md) §3.4).

**GET spatial-graph response (v1):**

```json
{
  "activeSceneId": "scene-hall",
  "nodes": [
    {
      "sceneId": "scene-hall",
      "locationName": "Hall",
      "isActive": true,
      "presentCount": 2,
      "structureId": "manor",
      "mapZone": "Ground floor",
      "mapShape": "rect",
      "mapSize": { "w": 18, "h": 12 },
      "layout": { "x": 50, "y": 50 },
      "mapPositionAuthor": { "x": 50, "y": 50 }
    },
    {
      "sceneId": "scene-kitchen",
      "locationName": "Kitchen",
      "isActive": false,
      "presentCount": 1,
      "structureId": "manor",
      "mapZone": "Ground floor",
      "mapShape": "rect",
      "mapSize": { "w": 14, "h": 10 },
      "layout": { "x": 50, "y": 28 }
    },
    {
      "sceneId": "scene-keep",
      "locationName": "Round Keep",
      "isActive": false,
      "presentCount": 0,
      "structureId": "keep",
      "mapZone": "Upper ward",
      "mapShape": "circle",
      "mapSize": { "w": 16, "h": 16 },
      "layout": { "x": 72, "y": 50 }
    },
    {
      "sceneId": "scene-bailey",
      "locationName": "Bailey",
      "isActive": false,
      "presentCount": 0,
      "layout": { "x": 72, "y": 78 }
    }
  ],
  "structures": [
    {
      "structureId": "manor",
      "displayName": "Manor House",
      "kind": "building",
      "containsActiveScene": true,
      "boundary": {
        "shape": "hull",
        "vertices": [
          { "x": 38, "y": 22 },
          { "x": 62, "y": 22 },
          { "x": 62, "y": 58 },
          { "x": 38, "y": 58 }
        ]
      }
    },
    {
      "structureId": "keep",
      "displayName": "Round Keep",
      "kind": "building",
      "containsActiveScene": false,
      "boundary": { "shape": "hull", "vertices": [] }
    }
  ],
  "edges": [
    {
      "exitId": "hall-kitchen-door",
      "sourceSceneId": "scene-hall",
      "targetSceneId": "scene-kitchen",
      "label": "Door to kitchen",
      "kind": "door",
      "travelSteps": 1,
      "direction": "N",
      "doorState": "closed",
      "exitAnchor": { "side": "N", "offset": 0.5 },
      "crossesStructure": false,
      "interiorOnly": true
    },
    {
      "exitId": "hall-bailey-gate",
      "sourceSceneId": "scene-hall",
      "targetSceneId": "scene-bailey",
      "label": "Postern gate",
      "kind": "door",
      "travelSteps": 1,
      "direction": "S",
      "crossesStructure": true
    }
  ],
  "layout": {
    "coordinateSpace": "normalized-0-100",
    "algorithm": "layered-bfs-v1",
    "architectureStyle": "diagram"
  }
}
```

v1.1+: `nodes[].mapShape`, `structureId`; `structures[].boundary`; `edges[].exitAnchor`, `crossesStructure`; world `architectureStyle`. See [14-web-ui.md](14-web-ui.md) §21.2–§21.3.

- `nodes[].layout` — `{ x, y }` in `0–100` space; clients render at these coordinates. Computed by server when scene has no `mapPosition` hint ([11-data-model.md](11-data-model.md)).
- `nodes[].mapPositionAuthor` — present only when world data supplied `mapPosition`; informational.
- `edges[]` — one row per exit from source scene; bidirectional worlds MAY emit reverse edges or client synthesizes reverse with same `travelSteps`.

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

## 10. Commissions (post-v1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/worlds/{worldId}/commissions` | List commissions |
| POST | `/worlds/{worldId}/commissions` | Create; default `deliverablePolicy: mind` (COM-1) |
| GET | `/worlds/{worldId}/commissions/{commissionId}` | Detail + `deliverableLocusKeys` |
| PATCH | `/worlds/{worldId}/commissions/{commissionId}` | Update status; `done` requires COM-2 |
| POST | `/worlds/{worldId}/commissions/{commissionId}/start` | Enqueue if assignee present at `targetSceneId` (COM-6) |
| POST | `/worlds/{worldId}/commissions/{commissionId}/force-complete` | Body `{ "reason": "..." }` |

**POST create body (illustrative):**

```json
{
  "assigneeCharacterId": "char-researcher",
  "targetSceneId": "scene-archives",
  "brief": "Summarize the WorldEngine GitHub README and API surface.",
  "deliverablePolicy": "mind"
}
```

Debate activity: `PATCH .../scenes/{sceneId}` with `activityJson` ([23-in-world-work.md](23-in-world-work.md)).

## 11. Approvals

| Method | Path | Description |
|--------|------|-------------|
| GET | `/approvals` | Pending list |
| POST | `/approvals/{approvalId}/approve` | |
| POST | `/approvals/{approvalId}/deny` | |

## 12. Inference health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health/llm` | Primary up |
| GET | `/health/embeddings` | Embed up |
| GET | `/inference/queue` | INF-5f global queue |

## 13. WebSocket events

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
| `commission.updated` | commissionId, status |

Client on reconnect: `GET` snapshot (world, active scene, roster, queue) then apply events where `eventSeq > lastSeen`.

## 15. Character authoring (v1 API sketch, Phase 3 UI)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/characters/draft` | `{ "brief": "..." }` — LLM draft ([24-character-authoring.md](24-character-authoring.md)) |
| GET | `/characters/draft/{draftId}` | Draft status + proposed `definitionJson` |
| POST | `/characters` | `{ "draftId", "definitionJson?" }` — approve and create |
| DELETE | `/characters/draft/{draftId}` | Discard draft |

## 16. Operator settings (v1.1 heartbeat)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/operator/settings` | Includes `heartbeat.enabled`, `heartbeat.intervalSeconds`, `lastHeartbeatAt` |
| PATCH | `/operator/settings` | Update global heartbeat ([08-real-world-capabilities.md](08-real-world-capabilities.md) HB-3) |

## 17. World package (v1.1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/worlds/{worldId}/package/export` | Zip: DB slice + `assets/` (DM-4) |
| POST | `/worlds/import` | Multipart package upload |

## 18. Requirements summary

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
- [23-in-world-work.md](23-in-world-work.md)
- [24-character-authoring.md](24-character-authoring.md)
