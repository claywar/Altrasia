# Altrasia Roadmap

Single-page view of milestones, repository status, and what ships when. Normative behavior remains in numbered specs `00`–`26`.

## Repository status

| Layer | Status |
|-------|--------|
| **Design specifications** | Complete (docs `00`–`26`, appendices, acceptance criteria) |
| **Implementation** | **Alpha** — Python backend, Web UI SPA, demo fixture; mock LLM default ([getting-started.md](guides/getting-started.md)) |
| **Shipped product** | **Alpha (local)** — spatial golden path + v1.1 + Phase 3–6 wedge in tree; see [IMPLEMENTATION-CHECKLIST.md](IMPLEMENTATION-CHECKLIST.md) |

Backlog phases T-001–T-081 are implemented; see [BACKLOG.md](BACKLOG.md). Optional: run nightly on reference GPU, `npm run test:e2e` in `web/`, release git tag.

## Product narrative (Acts)

| Act | Milestone | User-visible outcome | In tree |
|-----|-----------|----------------------|---------|
| **Act 1** | **v1** | Spatial world — multi-scene play, presence, scoped comms, memory, persona-first UI | Yes |
| **Act 2** | **v1.1** | Global heartbeat, phone play, world package export/import | Yes |
| **Act 3** | **Phase 4+** | Commissions, debate, commons, MapDraft, approvals | Wedge shipped; depth in BACKLOG |

## Milestones

### v1 — spatial wedge

**Outcome:** Solo operator plays as persona across scenes with memory discipline while the app runs.

**Release gate:** Spatial golden path + OQ-1/OQ-3 ([17-acceptance-criteria.md](17-acceptance-criteria.md)) — **passing in CI** (`tests/test_golden_path.py`).

**First-run:** `fixtureId: demo-spatial-v1` or `altrasia load-demo` — [guides/first-run-experience.md](guides/first-run-experience.md).

### v1.1 — persistence layer

**Outcome:** Idle when UI away; phone; portable packages — **implemented**.

### Post-v1 wedge (in tree)

| Capability | Status |
|------------|--------|
| Character authoring (CHAR) | API + Settings UI |
| Architect World / scene CRUD | Done |
| Commissions + debate | Runtime + UI |
| MapDraft + map grow | Done |
| Approvals, evidence, briefing | Done |
| World commons (MP-22) | API only — no Web UI panel |
| Minimal world map overlay | Done |
| Reflection (AO-8) | Done — default off |
| Idle social / banter | Done |
| Discussion deliverables | Done |

### Post-v1 depth (open implementation)

| Theme | Spec | Tracking |
|-------|------|----------|
| Real web/FS/scheduler (production) | [06](06-web-tools.md), [08](08-real-world-capabilities.md) | [SPEC-GAPS.md](SPEC-GAPS.md) |
| Plugin platform (full lifecycle) | [15](15-plugin-platform.md) | [SPEC-GAPS.md](SPEC-GAPS.md) |
| Full Phase 6 maps (MAP-ACC UI) | [18](18-location-maps.md), [25](25-map-authoring.md) | [SPEC-GAPS.md](SPEC-GAPS.md) |
| ComfyUI live integration | [19](19-comfyui-media.md) | [SPEC-GAPS.md](SPEC-GAPS.md) |
| AO-22 full activity overlays; scene harvest/inventory | [13](13-agent-orchestration.md), [05](05-tool-calling.md) | [SPEC-GAPS.md](SPEC-GAPS.md) |
| Commons Web UI | [23](23-in-world-work.md) | [SPEC-GAPS.md](SPEC-GAPS.md) |

## Feature matrix

| User-visible capability | v1 | v1.1 | Alpha wedge | Spec |
|-------------------------|:--:|:----:|:-----------:|------|
| Multi-scene + exits + presence | yes | | yes | [03](03-locations-and-presence.md) |
| Public / whisper / DM | yes | | yes | [04](04-communication.md) |
| Cross-scene knock | yes | | yes | [21](21-cross-scene-awareness.md) |
| Memory + mandatory recall | yes | | yes | [02](02-memory.md) |
| GpuResourceQueue + streaming UI | yes | | yes | [00](00-inference-runtime.md), [14](14-web-ui.md) |
| Observer Studio | yes | | yes | [09](09-roles-and-privilege.md) |
| Demo world `demo-spatial-v1` | yes | | yes | [fixture](../tests/fixtures/demo-world/README.md) |
| Phone play | | yes | yes | [04](04-communication.md) |
| Global heartbeat | | yes | yes | [08](08-real-world-capabilities.md) |
| World package | | yes | yes | [11](11-data-model.md) |
| Character authoring | | | yes | [24](24-character-authoring.md) |
| Commissions / debate | | | yes | [23](23-in-world-work.md) |
| MapDraft / map grow | | | yes | [25](25-map-authoring.md) |
| Mini-map structured | yes | | yes | [14](14-web-ui.md) §21.1 |
| Mini-map shapes / envelopes | | yes | partial | [14](14-web-ui.md) §21.2–21.3 |
| Full WorldMapCanvas + levels | | | partial (3D MapExplorer wedge) | [18](18-location-maps.md) |
| MAP-ACC full acceptance UI | | | no | [18](18-location-maps.md) |
| Live web/FS tools | | | partial | [06](06-web-tools.md), [08](08-real-world-capabilities.md) |
| ComfyUI portraits | | | partial | [19](19-comfyui-media.md) |
| Plugins | | | partial | [15](15-plugin-platform.md) |

## Build order (completed + ongoing)

1. **Sprint 1** — SQLite, memory, queue, tools — **done**
2. **Sprint 2** — Spatial wedge + Web UI — **done**
3. **Backlog phases** — [BACKLOG.md](BACKLOG.md)

## Deferred artifacts

| Artifact | Status |
|----------|--------|
| [getting-started.md](guides/getting-started.md) | Done |
| `CHANGELOG.md` | Done |
| OpenAPI from code | T-014 |
| Nightly real-LLM CI | T-010 |
| `SECURITY.md`, `CONTRIBUTING.md` | T-016 |
| Guide screenshots | T-073 |
| Stitch Pack A wireframes | Complete |

## Related documents

- [BACKLOG.md](BACKLOG.md) — interruptible task IDs
- [IMPLEMENTATION-CHECKLIST.md](IMPLEMENTATION-CHECKLIST.md)
- [20-product-principles.md](20-product-principles.md)
- [README.md](README.md)
