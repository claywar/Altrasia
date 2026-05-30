# 12 — API Sketch

REST and realtime surfaces for Altrasia v1 (single-operator). This is a sketch, not a full OpenAPI document.

**Implementation:** Served by the **Python backend**; consumed by the **Web UI SPA** and CLI ([26-system-architecture.md](26-system-architecture.md) SYS-3, SYS-6, SYS-13). Payloads are JSON; this sketch is language-agnostic.

**Single domain path:** Web UI actions, agent tools, narrative presence ([03-locations-and-presence.md](03-locations-and-presence.md) §7), and future scheduled jobs MUST call the same core services (presence, comms, memory, scene CRUD)—not parallel state machines with divergent rules.

## 0. Implementation status legend

Routes in this sketch use one of three labels when implementation differs from the normative target:

| Label | Meaning |
|-------|---------|
| **Release gate** | Required for v1/v1.1 CI; implemented as described |
| **Alpha wedge** | Implemented in tree; may differ from sketch path or be mock/off-by-default |
| **Spec target** | Normatively defined; **not yet in tree** ([SPEC-GAPS.md](SPEC-GAPS.md)) |

When **Implemented as** is noted, clients SHOULD use the implemented path until the spec target ships.

## 1. Transport

| Mechanism | Use |
|-----------|-----|
| REST | CRUD, commands |
| WebSocket or SSE | Events (`generation.*`, `scene.changed`, `queue.updated`) |
| SSE | Optional dedicated generation stream per job |

Auth v1: session cookie or `Authorization: Bearer` from env (`ALTRASIA_API_TOKEN`).

All world-scoped routes assume one operator; no multi-tenant headers.

## 2. Conventions

- Base path: `/api/v1`
- IDs are opaque strings (UUID recommended)
- Errors: `{ "error": { "code", "message" } }`
- Timestamps: ISO 8601 UTC
- Per-world **`eventSeq`** monotonic integer on WS events for reconnect ([11-data-model.md](11-data-model.md))

## 3. Worlds and scenes

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/worlds` | Release gate | List worlds |
| POST | `/worlds` | Release gate | Create world (wizard payload or `{ "fixtureId": "demo-spatial-v1" }`) |
| GET | `/worlds/{worldId}` | Release gate | World detail + active scene |
| PATCH | `/worlds/{worldId}` | Release gate | Update name, activeSceneId, config |
| GET | `/worlds/{worldId}/policy` | Alpha wedge | World policy toggles (reflection, idle social, citeProvenance, …) |
| PATCH | `/worlds/{worldId}/policy` | Alpha wedge | Partial policy update |
| POST | `/worlds/{worldId}/reset-fixture` | Alpha wedge | Reset demo world to fixture seed |
| GET | `/worlds/{worldId}/characters` | Alpha wedge | World cast list |
| POST | `/worlds/{worldId}/members` | Alpha wedge | Add character to world cast |
| GET | `/worlds/{worldId}/commons` | Alpha wedge | World commons loci (MP-22) |
| PUT | `/worlds/{worldId}/commons` | Alpha wedge | Replace world commons content |
| GET | `/worlds/{worldId}/scenes` | Release gate | List scenes |
| POST | `/worlds/{worldId}/scenes` | Release gate | Create scene |
| GET | `/worlds/{worldId}/scenes/{sceneId}` | Release gate | Scene header + presence |
| PATCH | `/worlds/{worldId}/scenes/{sceneId}` | Release gate | Rename, description, exits, `activityJson` |
| DELETE | `/worlds/{worldId}/scenes/{sceneId}` | Release gate | Reject if last scene (W-1) |
| GET | `/worlds/{worldId}/geography` | Alpha wedge | Geography + layout design mode |
| PATCH | `/worlds/{worldId}/geography` | Alpha wedge | Update geography fields |
| POST | `/worlds/{worldId}/geography/lock` | Alpha wedge | Lock geography for play |

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

**Presentation (Web UI):** `text` is stored as plain string; MAY include markdown and fenced `mermaid` blocks. Optional request field `contentFormat: "markdown"` is a hint for compose preview only—persistence unchanged. Rendering rules: [14-web-ui.md](14-web-ui.md) UI-R1–R8. Committed messages MUST NOT be deleted via API (UI-TRN-1).

**GET messages (assistant row, illustrative):** includes `streamStatus`, optional `generationJobId` for `SelectionRationalePopover` → `GET .../generations/{jobId}` ([11-data-model.md](11-data-model.md) §3.6).

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
| GET | `/worlds/{worldId}/navigation/summary` | Alpha wedge | Route graph summary for active scene |
| GET | `/worlds/{worldId}/navigation/route` | Alpha wedge | Query planned route between scenes |
| POST | `/worlds/{worldId}/navigation/travel` | Alpha wedge | Execute travel along route |
| POST | `/worlds/{worldId}/scenes/{sceneId}/exits/{exitId}/state` | Alpha wedge | Set exit door state (CC-11c) |

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

### 6.1 World map and levels (Phase 6)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/worlds/{worldId}/world-map` | Spec target | `worldMapArtifact`, site bounds ([18-location-maps.md](18-location-maps.md) §7) |
| GET | `/worlds/{worldId}/map-artifacts/site` | Alpha wedge | **Implemented as** site map artifact |
| GET | `/worlds/{worldId}/structures/{structureId}/levels` | Spec target | Scenes by `mapLevel`, vertical edges |
| GET | `/worlds/{worldId}/scenes/{sceneId}/map` | Spec target | Per-scene floor plan (MAP-1) |
| GET | `/worlds/{worldId}/scenes/{sceneId}/map-artifact` | Alpha wedge | **Implemented as** per-scene map artifact |

`spatial-graph` nodes (v1.1+): add `mapLevel`, `levelLabel`, `planPosition`; response MAY include `verticalEdges[]` where `exit.vertical === true`.

### 6.2 Layout drafts (Phase 6)

See [25-map-authoring.md](25-map-authoring.md). Schema: [`packages/schemas/map-layout-v1.schema.json`](../packages/schemas/map-layout-v1.schema.json).

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/worlds/{worldId}/layout-drafts` | Alpha wedge | Body `{ "brief", "scope", … }` → starts generation |
| POST | `/worlds/{worldId}/layout-bootstrap-drafts` | Alpha wedge | Bootstrap draft from existing world |
| POST | `/worlds/{worldId}/layout-drafts/unified` | Alpha wedge | Unified multi-surface draft |
| POST | `/worlds/{worldId}/layout-patch` | Alpha wedge | Apply layout patch without full draft |
| GET | `/worlds/{worldId}/layout-drafts/{draftId}` | Alpha wedge | `status`, `proposedJson`, `revision`, … |
| PATCH | `/worlds/{worldId}/layout-drafts/{draftId}` | Alpha wedge | Operator JSON edits → re-validate |
| POST | `/worlds/{worldId}/layout-drafts/{draftId}/repair` | Alpha wedge | Fix validation or describe change |
| POST | `/worlds/{worldId}/layout-drafts/{draftId}/commit` | Alpha wedge | Partial apply |
| GET | `/worlds/{worldId}/layout-drafts/{draftId}/preview.svg` | Spec target | SVG render of proposed layout |
| POST | `/worlds/{worldId}/layout-drafts/{draftId}/sync` | Spec target | `{ "source": "json" \| "visual" }` |
| POST | `/worlds/{worldId}/layout-drafts/{draftId}/resolve-conflict` | Spec target | Conflict resolution |
| DELETE | `/worlds/{worldId}/layout-drafts/{draftId}` | Spec target | Discard |

**POST layout-drafts body (illustrative):**

```json
{
  "brief": "Manor ground floor: hall central, kitchen north with door",
  "scope": "mini",
  "intent": "create"
}
```

**GET layout-drafts response (illustrative):**

```json
{
  "layoutDraftId": "draft-001",
  "status": "ready",
  "scope": "mini",
  "revision": 2,
  "proposedJson": { "schemaVersion": 1, "scope": "mini" },
  "changeList": [{ "kind": "scene_add", "sceneId": "scene-garden" }],
  "conflicts": [],
  "previewSvgUrl": "/worlds/w1/layout-drafts/draft-001/preview.svg"
}
```

## 7. Generation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/worlds/{worldId}/generate` | Enqueue GenerationJob |
| GET | `/worlds/{worldId}/queue` | Agent + GPU queue snapshot |
| POST | `/worlds/{worldId}/pause` | Pause world activity |
| POST | `/worlds/{worldId}/resume` | Resume |
| DELETE | `/inference/queue/{jobId}` | Cancel GPU job (INF-5g) |
| GET | `/worlds/{worldId}/generations/{jobId}/stream` | SSE token stream (STR-*) |
| GET | `/worlds/{worldId}/generations/{jobId}` | Job detail for rationale popover (UI-1, WF-21) |

**GET queue response (illustrative):**

```json
{
  "busy": true,
  "depth": 2,
  "estimatedWaitMs": 12000,
  "currentJob": {
    "jobId": "job-abc",
    "characterId": "char-alice",
    "sceneId": "scene-hall",
    "trigger": "persona_message",
    "continueDepth": 1,
    "status": "running",
    "selectionRationaleJson": {
      "pick": "addressed",
      "scores": {
        "char-alice": { "total": 0.92, "relevance": 0.82, "speechWeight": 0.5, "recency": -0.1 }
      }
    }
  }
}
```

**GET generations/{jobId} response (illustrative):**

```json
{
  "jobId": "job-abc",
  "status": "done",
  "characterId": "char-alice",
  "sceneId": "scene-hall",
  "messageId": "msg-xyz",
  "selectionRationaleJson": { "pick": "addressed", "scores": { "char-alice": { "total": 0.92 } } },
  "toolTraceJson": [
    { "tool": "memory_search", "argsSummary": "kettle", "ok": true }
  ]
}
```

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

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/worlds/{worldId}/observer/digest` | Release gate | Multi-scene digest (OBS-6) |
| POST | `/worlds/{worldId}/observer/generate` | Spec target | Observer generation with `observerMode` |

Use `POST /worlds/{worldId}/generate` with `characterId: observer` for Observer jobs in the Alpha tree.

## 9. Memory (operator)

**Alpha wedge:** Memory inspector routes are world-scoped under `/worlds/{worldId}/characters/{characterId}/…`.

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/worlds/{worldId}/characters/{characterId}/mind` | Alpha wedge | Mind pool loci |
| GET | `/worlds/{worldId}/characters/{characterId}/diary` | Alpha wedge | Diary segments |
| GET | `/worlds/{worldId}/characters/{characterId}/evidence` | Alpha wedge | Evidence records (MP-21) |
| GET | `/worlds/{worldId}/characters/{characterId}/memory-links` | Alpha wedge | MemoryLink graph edges |
| GET | `/worlds/{worldId}/characters/{characterId}/persona-proposals` | Alpha wedge | Pending PersonaProposal rows |
| POST | `/persona-proposals/{proposalId}/approve` | Alpha wedge | Approve persona update |
| POST | `/persona-proposals/{proposalId}/reject` | Alpha wedge | Reject persona update |
| GET | `/characters/{characterId}/loci` | Spec target | Legacy sketch path for mind pool |
| GET | `/scenes/{sceneId}/loci` | Spec target | World pool at scene |
| PATCH | `/characters/{characterId}/loci/{key}` | Spec target | Operator overwrite (MP-3) |

Agent tools (`memory_*`, `diary_*`) use internal paths during generation ([02-memory.md](02-memory.md)).

## 9b. Reflection (AO-8)

World policy keys: `reflectionEnabled`, `reflectionNightlyHourUtc`, `reflectionMaxCharsPerRun`, `reflectionAutoApproveLoci`, `reflectionLocusMaxChars`, `reflectionPersonaProposalsEnabled` ([16-learning.md](16-learning.md) §6).

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/worlds/{worldId}/reflect` | Alpha wedge | On-demand reflect all eligible cast |
| POST | `/characters/{characterId}/reflect` | Alpha wedge | On-demand reflect one character |
| GET | `/characters/{characterId}/reflection-runs` | Alpha wedge | Run history for Memory inspector |

## 10. Commissions and in-world work (Alpha wedge)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/worlds/{worldId}/commissions` | Alpha wedge | List commissions |
| POST | `/worlds/{worldId}/commissions` | Alpha wedge | Create; default `deliverablePolicy: mind` (COM-1) |
| GET | `/worlds/{worldId}/commissions/{commissionId}` | Spec target | Detail + `deliverableLocusKeys` |
| PATCH | `/worlds/{worldId}/commissions/{commissionId}` | Alpha wedge | Update status; `done` requires COM-2 |
| POST | `/worlds/{worldId}/commissions/{commissionId}/start` | Alpha wedge | Enqueue if assignee present (COM-6) |
| POST | `/worlds/{worldId}/commissions/{commissionId}/force-complete` | Alpha wedge | Body `{ "reason": "..." }` |

**POST create body (illustrative):**

```json
{
  "assigneeCharacterId": "char-researcher",
  "targetSceneId": "scene-archives",
  "brief": "Summarize the Altrasia GitHub README and API surface.",
  "deliverablePolicy": "mind"
}
```

Debate and briefing ([23-in-world-work.md](23-in-world-work.md)):

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/worlds/{worldId}/scenes/{sceneId}/debate` | Alpha wedge | Debate activity state |
| POST | `/worlds/{worldId}/scenes/{sceneId}/debate` | Alpha wedge | Start debate |
| PATCH | `/worlds/{worldId}/scenes/{sceneId}/debate` | Alpha wedge | Update debate activity |
| DELETE | `/worlds/{worldId}/scenes/{sceneId}/debate` | Alpha wedge | End debate |
| POST | `/worlds/{worldId}/scenes/{sceneId}/debate/advance-speaker` | Alpha wedge | DEB-2 speaker advance |
| POST | `/worlds/{worldId}/scenes/{sceneId}/debate/advance-phase` | Alpha wedge | Phase advance |
| POST | `/worlds/{worldId}/scenes/{sceneId}/briefing` | Alpha wedge | Apply briefing fixture to scene |

## 11. Approvals

**Alpha wedge:** Approvals are world-scoped.

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/worlds/{worldId}/approvals` | Alpha wedge | Pending list |
| POST | `/worlds/{worldId}/approvals/{approvalId}/approve` | Alpha wedge | Approve pending action |
| POST | `/worlds/{worldId}/approvals/{approvalId}/deny` | Alpha wedge | Deny pending action |
| GET | `/approvals` | Spec target | Global pending list (deprecated sketch) |
| POST | `/approvals/{approvalId}/approve` | Spec target | Global approve |
| POST | `/approvals/{approvalId}/deny` | Spec target | Global deny |

## 12. Inference health

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/health` | Release gate | Service up |
| GET | `/health/llm` | Release gate | Primary LLM up |
| GET | `/health/embeddings` | Spec target | Embed service up |
| GET | `/worlds/{worldId}/queue` | Release gate | Per-world agent + GPU queue (INF-5f) |
| DELETE | `/inference/queue/{jobId}` | Release gate | Cancel GPU job (INF-5g) |
| GET | `/inference/queue` | Spec target | Global queue snapshot |
| GET | `/operator/inference/models` | Alpha wedge | Model catalog for operator settings |

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

## 14. Character authoring (Alpha wedge)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/characters/draft` | Alpha wedge | `{ "brief": "..." }` — LLM draft ([24-character-authoring.md](24-character-authoring.md)) |
| GET | `/characters/draft/{draftId}` | Alpha wedge | Draft status + proposed `definitionJson` |
| POST | `/characters` | Alpha wedge | `{ "draftId", "definitionJson?" }` — approve and create |
| PATCH | `/characters/{characterId}` | Alpha wedge | Update character definition |
| DELETE | `/characters/draft/{draftId}` | Alpha wedge | Discard draft |

## 15. Operator settings (v1.1+)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/operator/settings` | Release gate | Heartbeat, inference, plugin flags |
| PATCH | `/operator/settings` | Release gate | Update global settings ([08-real-world-capabilities.md](08-real-world-capabilities.md) HB-3) |

Reflection policy is on **world** policy (`GET/PATCH /worlds/{worldId}/policy`), not operator settings.

## 16. World package (v1.1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/worlds/{worldId}/package/export` | Zip: DB slice + `assets/` (DM-4) |
| POST | `/worlds/import` | Multipart package upload |

## 17. Portrait (ComfyUI stub)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| POST | `/worlds/{worldId}/characters/{characterId}/portrait/generate` | Alpha wedge | Enqueue portrait job; mock when ComfyUI URL unset ([19-comfyui-media.md](19-comfyui-media.md)) |

## 18. Requirements summary

| ID | Requirement |
|----|-------------|
| API-1 | REST + WS/SSE for v1 operator console |
| API-2 | Meta messages isolated from scene transcript routes |
| API-3 | Streaming endpoint or WS tokens for STR-* |
| API-4 | Per-world eventSeq for ordering |
| API-5 | World-scoped memory and approval paths (Alpha wedge) |
| API-6 | Reflection and persona-proposal routes (AO-8) |

## Related documents

- [11-data-model.md](11-data-model.md)
- [14-web-ui.md](14-web-ui.md)
- [00-inference-runtime.md](00-inference-runtime.md)
- [16-learning.md](16-learning.md)
- [23-in-world-work.md](23-in-world-work.md)
- [24-character-authoring.md](24-character-authoring.md)
